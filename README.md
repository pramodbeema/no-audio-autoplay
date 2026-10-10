# No Audio Autoplay

An exteraGram plugin that stops Telegram from automatically advancing to
the next audio track or voice message when the current item finishes.

## Features

-   **Stops automatic progression** after a music or audio track ends
    naturally.
-   **Stops voice-message auto-advance** when a voice message or
    round-video message finishes.
-   **Preserves manual skipping** --- the Next action continues to work
    normally.
-   **On/off setting** --- disable the plugin's hooks to restore
    Telegram's default auto-advance behaviour.
-   **Playback cleanup** --- invokes the player's cleanup path when a
    music/audio track ends naturally.

## Compatibility

-   **Client:** exteraGram
-   **Minimum app version:** `12.5.1`
-   **Minimum plugin SDK version:** `1.4.4.3`
-   **Plugin version:** `1.2.0`

The plugin hooks internal Telegram `MediaController` methods. Those
implementation details may change in future Telegram or exteraGram
releases, so compatibility with versions beyond the stated requirements
is not guaranteed.

## Installation

1.  Make sure you are using a compatible version of exteraGram and its
    plugin SDK.
2.  Download `no_audio_autoplay.py` from this repository.
3.  Install or import the Python file using the plugin-loading workflow
    supported by your exteraGram installation.
4.  Enable **No Audio Autoplay** in the plugin settings.

The exact plugin import workflow can vary by exteraGram version. Follow
the installation guidance provided by your exteraGram build if it
differs from these general steps.

## Configuration

Open the plugin's settings and use **Disable automatic audio
progression**:

-   **ON:** playback stops at the end of the current audio or voice
    message instead of automatically proceeding to the next item.
-   **OFF:** the plugin removes its hooks, restoring Telegram's default
    auto-advance behaviour.

The setting is enabled by default.

## How It Works

The plugin hooks two methods in
`org.telegram.messenger.MediaController`:

### 1. Music and audio files

It hooks `playNextMessageWithoutOrder(boolean byStop)` before the
original method runs.

-   When `byStop` is `true` (natural playback end), the plugin calls
    `cleanupPlayer(true, true)` and skips the original method body to
    prevent automatic advancement.
-   When `byStop` is `false` (such as a manual Next action), it leaves
    the original behaviour unchanged.

### 2. Voice messages and round-video messages

It hooks `cleanupPlayer(boolean, boolean, boolean, boolean)`.

-   When the third argument, `byVoiceEnd`, is `true`, the plugin uses
    Java reflection to find and clear the `voiceMessagesPlaylist` field
    before the original method continues.
-   This prevents the original cleanup flow from selecting the next
    voice message while allowing the cleanup/notification path to run.

The plugin uses exteraGram's `BasePlugin` and `MethodHook` APIs, along
with Java reflection through the plugin environment.

## Repository Contents

-   `no_audio_autoplay_v1.2.0_working.py` --- plugin implementation.

If you rename the file for installation, retain the `.py` extension.

## Troubleshooting

-   **The plugin does not appear:** confirm that your exteraGram build
    supports Python plugins and that the file is in the location
    expected by your plugin loader.
-   **Automatic playback still occurs:** verify that the plugin is
    enabled and check the plugin logs for hook failures. The plugin logs
    whether each hook was installed successfully.
-   **Only some playback types are affected:** check the logs for
    failures involving `playNextMessageWithoutOrder` or `cleanupPlayer`;
    the two playback paths use separate hooks.
-   **After updating the client, the plugin stops working:** internal
    method names or signatures may have changed. Check compatibility
    with the installed exteraGram version.

## Limitations and Notes

-   The plugin depends on internal Telegram implementation details and
    Java reflection.
-   Hook installation can fail if a target method is missing or its
    signature changes. The plugin logs hook failures, but does not
    guarantee that both hooks will be available on every
    compatible-looking build.
-   The plugin does not change Telegram's playlists or playback settings
    globally; it intercepts the relevant playback progression paths
    while enabled.

## Author

-   **Plugin author:** [@PramodBeema](https://t.me/PramodBeema)
-   **Original code comment credit:** Kiro

## License

No license is specified in the provided source file. Unless a license is
added to the repository, reuse and redistribution permissions are not
explicitly granted. Add a `LICENSE` file if you want to specify terms
for others to use, modify, or redistribute the project.
