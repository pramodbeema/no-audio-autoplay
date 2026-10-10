##
## no_audio_autoplay.py — exteraGram plugin
##
## Disables automatic progression to the next audio/voice track after
## the currently playing one finishes in any chat.
##
## ── Verified against Telegram Android open source (DrKLO/Telegram) ──────────
##
##  1. Music / audio files
##     ExoPlayer STATE_ENDED → anonymous delegate in playMessage() calls:
##         playNextMessageWithoutOrder(true)   [private, boolean byStop]
##     We hook this method in "before" mode.  When byStop=true (natural end)
##     we call cleanupPlayer(true, true) ourselves and then set a void result
##     to skip the original body.  When byStop=false (manual Next button) we
##     do nothing, so the original runs normally.
##
##  2. Voice / round-video messages
##     cleanupPlayer(notify, stopService, byVoiceEnd=true, ...) reads
##     voiceMessagesPlaylist and calls playMessage(nextVoice).
##     We hook in "before" mode: when byVoiceEnd=true we null out the
##     voiceMessagesPlaylist field via Java reflection so the original body
##     finds an empty playlist and skips to the "messagePlayingDidReset"
##     notification path.
##
## Author: Kiro (generated for PramodBeema)
## Compatible with: exteraGram 12.5.1+  /  SDK 1.4.4.3+
##

# ── Plugin metadata ──────────────────────────────────────────────────────────
__id__          = "no_audio_autoplay"
__name__        = "No Audio Autoplay"
__description__ = (
    "Stops Telegram from automatically playing the next audio or voice "
    "message after the current one finishes. Playback ends cleanly at "
    "the track you chose."
)
__author__      = "@PramodBeema"
__version__     = "1.2.0"
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.4.3"

# ── Imports ──────────────────────────────────────────────────────────────────
from base_plugin import BasePlugin, MethodHook
from ui.settings import Header, Switch, Text
from java import jclass  # type: ignore
from java.lang import Boolean  # type: ignore

# ── Constants ────────────────────────────────────────────────────────────────
MEDIA_CONTROLLER_CLASS = "org.telegram.messenger.MediaController"
PLAY_NEXT_AUTO  = "playNextMessageWithoutOrder"   # private void (boolean byStop)
CLEANUP_PLAYER  = "cleanupPlayer"                 # public  void (bool, bool, bool, bool)
VOICE_PLAYLIST  = "voiceMessagesPlaylist"         # ArrayList field


# ── Helper: get a declared field traversing the class hierarchy ───────────────

def _find_declared_field(cls, field_name):
    """Walk up the class hierarchy to find a declared field by name."""
    klass = cls
    while klass is not None:
        try:
            f = klass.getDeclaredField(field_name)
            f.setAccessible(True)
            return f
        except Exception:
            klass = klass.getSuperclass()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Hook 1 — stop music/audio auto-advance
# ─────────────────────────────────────────────────────────────────────────────

class _StopMusicAutoplay(MethodHook):
    """
    Intercepts playNextMessageWithoutOrder(boolean byStop) before it runs.

    byStop=True  → track ended naturally → stop cleanly, skip original body.
    byStop=False → user pressed Next    → let original run (manual skip works).
    """

    def before_hooked_method(self, param):
        by_stop = bool(param.args[0])
        if not by_stop:
            return  # manual skip — don't interfere

        # Natural end: call cleanupPlayer(notify=true, stopService=true)
        # and then block the original advance body.
        mc = param.thisObject
        try:
            cleanup = mc.getClass().getMethod(
                CLEANUP_PLAYER, Boolean.TYPE, Boolean.TYPE
            )
            cleanup.invoke(mc, True, True)
        except Exception:
            pass  # even if cleanup fails, blocking the advance is the priority

        param.setResult(None)  # void — skip original playNextMessageWithoutOrder


# ─────────────────────────────────────────────────────────────────────────────
# Hook 2 — stop voice-message auto-advance
# ─────────────────────────────────────────────────────────────────────────────

class _StopVoiceAutoplay(MethodHook):
    """
    Intercepts cleanupPlayer(notify, stopService, byVoiceEnd, transfer).

    When byVoiceEnd=True the original reads voiceMessagesPlaylist and
    auto-plays the next voice note.  We null out that field before the
    original runs so it finds nothing and skips to the stop/notify path.
    """

    def before_hooked_method(self, param):
        by_voice_end = bool(param.args[2])
        if not by_voice_end:
            return

        mc = param.thisObject
        try:
            field = _find_declared_field(mc.getClass(), VOICE_PLAYLIST)
            if field is not None:
                field.set(mc, None)
        except Exception:
            pass
        # No setResult — let cleanupPlayer run (it now sees null playlist).


# ─────────────────────────────────────────────────────────────────────────────
# Plugin class
# ─────────────────────────────────────────────────────────────────────────────

class NoAudioAutoplayPlugin(BasePlugin):

    def on_plugin_load(self):
        self.logger.info("no_audio_autoplay: loading")
        self._hooks = []
        self._applied = False

        if self.get_setting("enabled", True):
            self._apply_hooks()

    def on_plugin_unload(self):
        self.logger.info("no_audio_autoplay: unloading")
        self._remove_hooks()

    # ── Settings ──────────────────────────────────────────────────────────

    def create_settings(self):
        return [
            Header(text="No Audio Autoplay"),
            Switch(
                key="enabled",
                text="Disable automatic audio progression",
                subtext=(
                    "When ON, playback stops after the current audio or voice "
                    "message ends. When OFF, Telegram's default auto-advance "
                    "behaviour is restored."
                ),
                default=True,
                on_change=self._on_toggle,
            ),
            Text(
                text="How it works",
                subtext=(
                    "Hooks MediaController.playNextMessageWithoutOrder "
                    "(music/audio) and MediaController.cleanupPlayer "
                    "(voice messages) via Xposed to stop automatic advancement."
                ),
            ),
        ]

    # ── Hook management ───────────────────────────────────────────────────

    def _apply_hooks(self):
        if self._applied:
            return
        try:
            # Use jclass() — the pattern confirmed by real exteraGram plugins.
            mc_class = jclass(MEDIA_CONTROLLER_CLASS).getClass()

            # ── Hook 1: playNextMessageWithoutOrder(boolean) ──────────────
            try:
                m1 = mc_class.getDeclaredMethod(PLAY_NEXT_AUTO, Boolean.TYPE)
                m1.setAccessible(True)
                self._hooks.append(self.hook_method(m1, _StopMusicAutoplay()))
                self.logger.info("no_audio_autoplay: hooked %s ✓", PLAY_NEXT_AUTO)
            except Exception as e:
                self.logger.error("no_audio_autoplay: %s hook failed — %s", PLAY_NEXT_AUTO, e)

            # ── Hook 2: cleanupPlayer(bool, bool, bool, bool) ─────────────
            try:
                m2 = mc_class.getDeclaredMethod(
                    CLEANUP_PLAYER,
                    Boolean.TYPE, Boolean.TYPE, Boolean.TYPE, Boolean.TYPE,
                )
                m2.setAccessible(True)
                self._hooks.append(self.hook_method(m2, _StopVoiceAutoplay()))
                self.logger.info("no_audio_autoplay: hooked %s ✓", CLEANUP_PLAYER)
            except Exception as e:
                self.logger.error("no_audio_autoplay: %s hook failed — %s", CLEANUP_PLAYER, e)

            if self._hooks:
                self._applied = True
                self.logger.info(
                    "no_audio_autoplay: %d hook(s) active — autoplay disabled.",
                    len(self._hooks),
                )

        except Exception as e:
            self.logger.exception("no_audio_autoplay: unexpected error: %s", e)

    def _remove_hooks(self):
        for h in self._hooks:
            try:
                h.unhook()
            except Exception as e:
                self.logger.warning("no_audio_autoplay: unhook error: %s", e)
        self._hooks.clear()
        self._applied = False
        self.logger.info("no_audio_autoplay: hooks removed — autoplay restored.")

    def _on_toggle(self, enabled: bool):
        if enabled:
            self._apply_hooks()
        else:
            self._remove_hooks()
