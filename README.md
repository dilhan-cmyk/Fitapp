# Fuel for Android: how to build and install

You do not need Android Studio. GitHub builds the app for you.

## 1. Put the files on GitHub (once)
1. Go to github.com > New repository. Name it `fuel-app`, choose **Private**, click Create.
2. Click "uploading an existing file". Unzip this folder on your computer, then drag EVERYTHING inside it into the page
   (package.json, capacitor.config.json, fuel.keystore, build-apk-workflow.yml, and the folders www, native, scripts). Click Commit.
3. The hidden `.github` folder often does not upload. So check: if your repo has no `.github/workflows/build-apk.yml`, do this:
   Add file > Create new file. In the name box type exactly `.github/workflows/build-apk.yml`
   (typing the slashes creates the folders). Paste in the whole contents of `build-apk-workflow.yml`. Click Commit.

## 2. Build the APK
1. Open the **Actions** tab. Click "Build Android APK" on the left, then **Run workflow**. (It also runs when you upload files.)
2. Wait about 5 to 10 minutes. A green tick means it worked.
3. Click the finished run. At the bottom, under **Artifacts**, download **Fuel-APK**. Unzip it to get `app-debug.apk`.

If the run shows a red cross: open it, click the failed step, copy the last 40 or so lines of the error, and send them to me.

## 3. Install on your phone
1. Get `app-debug.apk` onto your phone (email it to yourself, Google Drive, or USB).
2. Tap it. Android will ask you to allow installs from that app (Files, Drive or Chrome). Allow it for this one install.
3. If Play Protect says it's an unknown app, tap More details > Install anyway. (It's your own app, signed with your own key.)
4. Open **Fuel**. Open the Weight tab and tap "Import my Google Fit history".
5. On the Today screen tap **Connect Health Connect to sync steps** and allow Steps.

## Moving data from the web version (only if you already use it)
Web version: Settings > Backup (JSON). Send the file to your phone. In the new app: Settings > Restore backup.

## Updating later
Upload the changed files over the old ones in GitHub, run the workflow again, and install the new APK over the top.
Do NOT uninstall first: your data stays because the app is always signed with the same key (fuel.keystore).
Back up now and then: Settings > Backup (JSON) opens the share sheet so you can save it to Drive.
