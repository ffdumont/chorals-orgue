/* Synchronise un curseur OpenSheetMusicDisplay avec une video YouTube.
   Scanne tous les .sync-block du DOM et initialise une instance par bloc.
   Requiert window.opensheetmusicdisplay (charge en amont) et window.YT
   (injecte par ce script). */
(function () {
  "use strict";

  var pendingForYt = [];
  var ytApiReady = false;

  window.onYouTubeIframeAPIReady = function () {
    ytApiReady = true;
    pendingForYt.splice(0).forEach(initYtPlayer);
  };

  function injectYtApi() {
    if (document.getElementById("yt-iframe-api-script")) return;
    var s = document.createElement("script");
    s.id = "yt-iframe-api-script";
    s.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(s);
  }

  function initBlock(block) {
    var midiKey = block.dataset.midiKey;
    var scoresBase = block.dataset.scoresBase || "/assets/scores/";
    var osmdDiv = block.querySelector(".osmd-host");
    var offsetInput = block.querySelector(".offset-input");
    var cursorCheckbox = block.querySelector(".cursor-checkbox");
    var statusEl = block.querySelector(".status");

    var state = {
      block: block,
      osmd: null,
      timemap: null,
      cursorStep: 0,
      ytPlayer: null,
      offsetInput: offsetInput,
      statusEl: statusEl,
      running: false,
    };
    block._syncState = state;

    Promise.all([
      fetch(scoresBase + midiKey + ".musicxml").then(function (r) {
        if (!r.ok) throw new Error("MusicXML HTTP " + r.status);
        return r.text();
      }),
      fetch(scoresBase + midiKey + ".timemap.json").then(function (r) {
        if (!r.ok) throw new Error("timemap HTTP " + r.status);
        return r.json();
      }),
    ])
      .then(function (vals) {
        var xml = vals[0];
        var map = vals[1];
        state.timemap = map.onsets;

        // Proto-style minimal config: OSMD's default cursor works here.
        // We DO NOT use renderSingleHorizontalStaffline — it was breaking
        // cursor visibility in some combinations. Score may wrap onto
        // multiple systems; that's an acceptable trade-off for now.
        var osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay(osmdDiv, {
          autoResize: false,
          drawTitle: false,
          drawSubtitle: false,
          drawComposer: false,
          followCursor: true,
          pageFormat: "Endless",
          drawingParameters: "compact",
          // OSMD cursor is kept invisible (alpha=0); we draw our own
          // visible overlay (see customCursor below) since the theme's
          // global `img` CSS was killing OSMD's native cursor rendering.
          cursorsOptions: [{ color: "#000000", alpha: 0.0, type: 0, follow: true }],
        });
        state.osmd = osmd;
        return osmd.load(xml).then(function () {
          osmd.render();
          osmd.cursor.show();
          fitHeights(block, osmdDiv);

          var scoreWrap = block.querySelector(".score-wrap");
          // DEBUG: wide red bar to confirm our overlay shows up at all.
          // If this is invisible, something structural is wrong (stacking,
          // overflow, or element not actually appended); if it shows, we
          // can narrow it down and position it via OSMD cursor's location.
          var customCursor = document.createElement("div");
          customCursor.style.cssText =
            "position:absolute;" +
            "width:40px;" +           // wide for visibility test
            "background:red;" +       // solid red, no transparency
            "pointer-events:none;" +
            "z-index:9999;" +
            "top:0;" +
            "left:0;" +
            "height:100%;" +
            "display:block;" +
            "box-shadow:0 0 0 2px yellow;";  // yellow outline
          osmdDiv.appendChild(customCursor);

          // Also attach to .score-wrap as a secondary test in case
          // something scopes or hides things inside .osmd-host.
          var fallbackCursor = document.createElement("div");
          fallbackCursor.style.cssText =
            "position:absolute;" +
            "width:6px;" +
            "background:magenta;" +
            "pointer-events:none;" +
            "z-index:9998;" +
            "top:0;" +
            "left:0;" +
            "height:100%;" +
            "display:block;";
          if (scoreWrap) {
            scoreWrap.style.position = "relative";
            scoreWrap.appendChild(fallbackCursor);
          }
          state.fallbackCursor = fallbackCursor;
          state.customCursor = customCursor;
          state.osmdDiv = osmdDiv;

          if (scoreWrap) scoreWrap.scrollLeft = 0;

          // Report DOM tree so we can see what's actually inside osmd-host
          var kids = Array.prototype.map.call(osmdDiv.children, function(c){
            return c.tagName.toLowerCase() +
              (c.id ? "#" + c.id : "") +
              (c.className && typeof c.className === "string" ? "." + c.className : "");
          }).join(", ");
          statusEl.textContent =
            "onsets=" + state.timemap.length +
            " | osmd-host children: " + kids;

          if (cursorCheckbox) {
            cursorCheckbox.addEventListener("change", function () {
              if (state.customCursor) {
                state.customCursor.style.display = cursorCheckbox.checked ? "block" : "none";
              }
            });
          }

          if (ytApiReady) initYtPlayer(block);
          else pendingForYt.push(block);
        });
      })
      .catch(function (err) {
        statusEl.textContent = "Erreur chargement: " + err.message;
        statusEl.classList.add("warn");
        console.error(err);
      });
  }

  function initYtPlayer(block) {
    var state = block._syncState;
    if (!state) return;
    var iframe = block.querySelector(".sync-player");
    if (!iframe.id) iframe.id = "sync-player-" + Math.random().toString(36).slice(2, 10);
    state.ytPlayer = new YT.Player(iframe.id, {
      events: {
        onReady: function () {
          state.statusEl.textContent += " | Video prete.";
        },
        onStateChange: function (e) {
          if (e.data === YT.PlayerState.PLAYING && !state.running) {
            state.running = true;
            requestAnimationFrame(function () { syncLoop(state); });
          }
        },
      },
    });
  }

  // Fit the score-wrap to the actually-rendered SVG height. The video-wrap
  // is aligned to the same height; its 16:9 aspect ratio drives its width.
  function fitHeights(block, osmdDiv) {
    var scoreWrap = block.querySelector(".score-wrap");
    var videoWrap = block.querySelector(".video-wrap");
    if (!scoreWrap) return;
    var svg = osmdDiv.querySelector("svg");
    var contentH = svg ? svg.getBoundingClientRect().height : osmdDiv.scrollHeight;
    var minH = 260;
    var maxH = Math.min(window.innerHeight * 0.6, 520);
    var target = Math.max(minH, Math.min(contentH + 16, maxH));
    scoreWrap.style.height = target + "px";
    if (videoWrap) videoWrap.style.height = target + "px";
  }

  function resetCursorTo(state, t) {
    state.osmd.cursor.reset();
    state.cursorStep = 0;
    while (state.cursorStep < state.timemap.length && state.timemap[state.cursorStep] <= t) {
      state.osmd.cursor.next();
      state.cursorStep++;
    }
  }

  // Read OSMD cursor's actual rendered position via offsetLeft/offsetTop
  // (works regardless of whether OSMD uses style.left or HTML attributes)
  // and apply it to our visible custom cursor div.
  function syncCustomCursor(state) {
    if (!state.osmdDiv || !state.customCursor) return;
    // OSMD exposes .cursor which has an internal cursorElement in most versions
    var el = null;
    var c = state.osmd && state.osmd.cursor;
    if (c) el = c.cursorElement || (c.cursorElements && c.cursorElements[0]);
    // Fallback: find any absolute-positioned img inside the container
    if (!el) {
      var imgs = state.osmdDiv.querySelectorAll("img");
      for (var i = 0; i < imgs.length; i++) {
        var img = imgs[i];
        if (img.style && img.style.position === "absolute") { el = img; break; }
      }
      if (!el && imgs.length) el = imgs[imgs.length - 1];
    }
    if (!el) return;
    var left = el.offsetLeft;
    var top = el.offsetTop;
    var height = el.offsetHeight;
    if (isFinite(left)) state.customCursor.style.left = left + "px";
    if (isFinite(top) && top > 0) state.customCursor.style.top = top + "px";
    if (isFinite(height) && height > 0) state.customCursor.style.height = height + "px";
  }

  function syncLoop(state) {
    if (!state.ytPlayer || typeof state.ytPlayer.getCurrentTime !== "function") {
      requestAnimationFrame(function () { syncLoop(state); });
      return;
    }
    var offset = parseFloat(state.offsetInput.value) || 0;
    var t = state.ytPlayer.getCurrentTime() - offset;

    var moved = false;
    if (state.cursorStep > 0 && state.timemap[state.cursorStep - 1] > t + 0.25) {
      resetCursorTo(state, t);
      moved = true;
    } else {
      while (state.cursorStep < state.timemap.length && state.timemap[state.cursorStep] <= t) {
        state.osmd.cursor.next();
        state.cursorStep++;
        moved = true;
      }
    }
    if (moved) syncCustomCursor(state);

    if (state.statusEl) {
      state.statusEl.textContent =
        "step " + state.cursorStep + "/" + state.timemap.length +
        " t=" + t.toFixed(1);
    }

    requestAnimationFrame(function () { syncLoop(state); });
  }

  function waitForOsmdThenInit() {
    if (typeof opensheetmusicdisplay === "undefined") {
      setTimeout(waitForOsmdThenInit, 50);
      return;
    }
    injectYtApi();
    document.querySelectorAll(".sync-block").forEach(initBlock);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", waitForOsmdThenInit);
  } else {
    waitForOsmdThenInit();
  }
})();
