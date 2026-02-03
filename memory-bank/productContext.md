# Watchtime Tracker - Product Context

## Overview

**Watchtime Tracker** is a cross-browser extension (Chrome, Firefox, Opera) that tracks watch statistics for YouTube and Twitch. It provides users with detailed analytics about their viewing habits.

## Core Purpose

- Track time spent watching YouTube videos and Twitch streams
- Aggregate statistics by channel, day, week
- Provide visual analytics (charts, tables) in a popup interface
- Sync data across devices via Firebase authentication

## Target Platforms

| Platform | Manifest | Output               | Status        |
| -------- | -------- | -------------------- | ------------- |
| Chrome   | MV3      | `extension/chrome/`  | ✅ Active     |
| Firefox  | MV2      | `extension/firefox/` | ⚠️ Deprecated |
| Opera    | MV3      | `extension/opera/`   | ⚠️ Deprecated |

> **Note**: Only Chrome is actively supported. Firefox and Opera builds exist but are no longer maintained.

## Key Features

1. **YouTube Tracking**: Video watch time, channel statistics, live stream support
2. **Twitch Tracking**: Stream watch time by streamer
3. **User Authentication**: Guest mode, email/password, Google sign-in
4. **Data Visualization**: Bar charts (weekly avg), pie charts, data tables
5. **Cross-Device Sync**: Firebase Firestore for remote storage
6. **Offline Support**: IndexedDB (Dexie) for local caching

## Tech Stack

| Category      | Technology                 |
| ------------- | -------------------------- |
| Language      | TypeScript                 |
| UI Framework  | React (aliased to Preact)  |
| UI Components | Material-UI (MUI) v7       |
| Charts        | Nivo (bar, pie)            |
| Build         | Webpack                    |
| Backend       | Firebase (Auth, Firestore) |
| Local Storage | IndexedDB via Dexie        |
| Browser API   | webextension-polyfill      |

## Version

Current: **v2.4.1**
