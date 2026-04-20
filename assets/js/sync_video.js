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
        });
        state.osmd = osmd;
        return osmd.load(xml).then(function () {
          osmd.render();
          // Match what worked in the standalone proto: show() only, no reset().
          osmd.cursor.show();
          fitHeights(block, osmdDiv);

          var scoreWrap = block.querySelector(".score-wrap");
          if (scoreWrap) scoreWrap.scrollLeft = 0;

          // Debug snapshot: what did OSMD actually put in the container?
          var imgCount = osmdDiv.querySelectorAll("img").length;
          var svgCount = osmdDiv.querySelectorAll("svg").length;
          statusEl.textContent =
            "Partition OK (" + state.timemap.length + " onsets, " +
            svgCount + " svg, " + imgCount + " img).";

          if (cursorCheckbox) {
            cursorCheckbox.addEventListener("change", function () {
              if (cursorCheckbox.checked) osmd.cursor.show();
              else osmd.cursor.hide();
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

  function syncLoop(state) {
    if (!state.ytPlayer || typeof state.ytPlayer.getCurrentTime !== "function") {
      requestAnimationFrame(function () { syncLoop(state); });
      return;
    }
    var offset = parseFloat(state.offsetInput.value) || 0;
    var t = state.ytPlayer.getCurrentTime() - offset;

    if (state.cursorStep > 0 && state.timemap[state.cursorStep - 1] > t + 0.25) {
      resetCursorTo(state, t);
    } else {
      while (state.cursorStep < state.timemap.length && state.timemap[state.cursorStep] <= t) {
        state.osmd.cursor.next();
        state.cursorStep++;
      }
    }

    // Debug live status: step + whether an OSMD cursor <img> is in the DOM
    // and what its dimensions are. Helps diagnose "invisible cursor" cases.
    if (state.statusEl && state.block) {
      var osmdDiv = state.block.querySelector(".osmd-host");
      var imgs = osmdDiv ? osmdDiv.querySelectorAll("img") : [];
      var info = "no-img";
      if (imgs.length) {
        var last = imgs[imgs.length - 1];
        info = imgs.length + "img " +
          Math.round(last.getBoundingClientRect().width) + "x" +
          Math.round(last.getBoundingClientRect().height) +
          " @" + Math.round(parseFloat(last.style.left) || 0);
      }
      state.statusEl.textContent =
        "step " + state.cursorStep + "/" + state.timemap.length +
        " t=" + t.toFixed(1) + " " + info;
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
