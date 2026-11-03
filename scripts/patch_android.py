"""Run after `npx cap add android`. Adds Health Connect, camera, signing and icons."""
import glob, os, re, shutil

A = 'android'
def rd(p): return open(p, encoding='utf8').read()
def wr(p, s): open(p, 'w', encoding='utf8').write(s)
def step(msg): print('==>', msg, flush=True)

# 1. minSdk 26 (needed by Health Connect)
step('minSdk 26')
p = f'{A}/variables.gradle'
s = rd(p)
s, n = re.subn(r'minSdkVersion\s*=\s*\d+', 'minSdkVersion = 26', s)
assert n == 1, 'minSdkVersion not found in variables.gradle'
wr(p, s)

# 2. Kotlin Gradle plugin (the Health Connect plugin is written in Kotlin)
step('Kotlin plugin')
p = f'{A}/build.gradle'
s = rd(p)
if 'kotlin-gradle-plugin' not in s:
    s, n = re.subn(r'(buildscript\s*\{.*?dependencies\s*\{)',
                   r'\1\n        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.24"',
                   s, count=1, flags=re.S)
    assert n == 1, 'buildscript dependencies block not found'
wr(p, s)

# 3. App module: Kotlin, dependencies, stable signing key
step('app/build.gradle')
p = f'{A}/app/build.gradle'
s = rd(p)
assert "apply plugin: 'com.android.application'" in s, 'unexpected app/build.gradle'
if "kotlin-android" not in s:
    s = s.replace("apply plugin: 'com.android.application'",
                  "apply plugin: 'com.android.application'\napply plugin: 'kotlin-android'", 1)
s += '''

android {
    defaultConfig {
        ndk { abiFilters "arm64-v8a" }
    }
    signingConfigs {
        debug {
            storeFile file("$rootDir/fuel.keystore")
            storePassword "fuelfuel"
            keyAlias "fuel"
            keyPassword "fuelfuel"
            v1SigningEnabled true
            v2SigningEnabled true
        }
    }
    kotlinOptions {
        jvmTarget = '17'
    }
}

dependencies {
    implementation "androidx.health.connect:connect-client:1.1.0-alpha07"
    implementation "org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3"
    implementation "com.google.mlkit:text-recognition:16.0.1"
}
'''
build_no = os.environ.get('GITHUB_RUN_NUMBER', '1')
s, n1 = re.subn(r'versionCode\s+\d+', f'versionCode {build_no}', s, count=1)
s, n2 = re.subn(r'versionName\s+"[^"]*"', f'versionName "1.{build_no}"', s, count=1)
print(f'version -> 1.{build_no} (code {build_no}); patched {n1}+{n2}')
wr(p, s)
shutil.copy('fuel.keystore', f'{A}/fuel.keystore')

# 4. Native plugin + MainActivity
step('plugin + MainActivity')
mains = glob.glob(f'{A}/app/src/main/java/**/MainActivity.java', recursive=True)
assert mains, 'MainActivity.java not found'
main = mains[0]
pkg = re.search(r'package\s+([\w.]+);', rd(main)).group(1)
dst = os.path.dirname(main)
for name in ('HealthStepsPlugin.kt', 'UpdaterPlugin.kt', 'LabelOcrPlugin.kt'):
    kt = rd(f'native/{name}')
    kt = re.sub(r'^package\s+[\w.]+', f'package {pkg}', kt, count=1, flags=re.M)
    wr(os.path.join(dst, name), kt)
wr(main, f'''package {pkg};

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {{
    @Override
    public void onCreate(Bundle savedInstanceState) {{
        registerPlugin(HealthStepsPlugin.class);
        registerPlugin(UpdaterPlugin.class);
        registerPlugin(LabelOcrPlugin.class);
        super.onCreate(savedInstanceState);
    }}
}}
''')

# 5. Manifest: permissions, Health Connect rationale, camera
step('AndroidManifest')
p = f'{A}/app/src/main/AndroidManifest.xml'
s = rd(p)
perm = '''    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.health.READ_STEPS" />
    <queries>
        <package android:name="com.google.android.apps.healthdata" />
    </queries>
'''
if 'READ_STEPS' not in s:
    assert '<application' in s
    s = s.replace('<application', perm + '    <application', 1)
    rationale = '''            <intent-filter>
                <action android:name="androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE" />
            </intent-filter>
        </activity>
        <activity-alias
            android:name="ViewPermissionUsageActivity"
            android:exported="true"
            android:targetActivity=".MainActivity"
            android:permission="android.permission.START_VIEW_PERMISSION_USAGE">
            <intent-filter>
                <action android:name="android.intent.action.VIEW_PERMISSION_USAGE" />
                <category android:name="android.intent.category.HEALTH_PERMISSIONS" />
            </intent-filter>
        </activity-alias>'''
    assert '</activity>' in s
    s = s.replace('</activity>', rationale, 1)
if 'REQUEST_INSTALL_PACKAGES' not in s:
    s = s.replace('<application', '    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />\n    <application', 1)
    provider = '''        <provider
            android:name=".UpdateFileProvider"
            android:authorities="${applicationId}.updates"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/fuel_update_paths" />
        </provider>
    '''
    assert '</application>' in s
    s = s.replace('</application>', provider + '</application>', 1)
wr(p, s)
os.makedirs(f'{A}/app/src/main/res/xml', exist_ok=True)
wr(f'{A}/app/src/main/res/xml/fuel_update_paths.xml',
   '<?xml version="1.0" encoding="utf-8"?>\n<paths xmlns:android="http://schemas.android.com/apk/res/android">\n    <cache-path name="update" path="update/" />\n</paths>\n')

# 6. App icon (best effort; never fails the build)
step('icons')
try:
    from PIL import Image, ImageDraw
    SRC = Image.open('assets/icon-source.png').convert('RGBA')
    def draw(size, transparent):
        # transparent=True -> adaptive foreground (photo inside the safe zone)
        # transparent=False -> legacy launcher icon (photo on dark background)
        im = Image.new('RGBA', (size, size), (0, 0, 0, 0) if transparent else (15, 22, 33, 255))
        s = int(size * (0.72 if transparent else 1.0))
        p = SRC.resize((s, s), Image.LANCZOS)
        im.alpha_composite(p, ((size - s) // 2, (size - s) // 2 + (int(size * 0.04) if transparent else 0)))
        return im
    legacy = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
    fg = {'mdpi': 108, 'hdpi': 162, 'xhdpi': 216, 'xxhdpi': 324, 'xxxhdpi': 432}
    res = f'{A}/app/src/main/res'
    for k in legacy:
        d = f'{res}/mipmap-{k}'
        if not os.path.isdir(d): continue
        for name in ('ic_launcher.png', 'ic_launcher_round.png'):
            draw(legacy[k], False).save(f'{d}/{name}')
        draw(fg[k], True).save(f'{d}/ic_launcher_foreground.png')
    bg = f'{res}/values/ic_launcher_background.xml'
    if os.path.exists(bg):
        wr(bg, '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">#0F1621</color>\n</resources>\n')
except Exception as e:
    print('icon step skipped:', e)

print('patch complete')
