/* Synchronise un curseur OpenSheetMusicDisplay avec une video YouTube.
   Scanne tous les .sync-block du DOM et initialise une instance par bloc.
   Requiert window.opensheetmusicdisplay (charge en amont) et window.YT
   (injecte par ce script). */
(function () {
  "use strict";

  var pendingForYt = [];
  var ytApiReady = false;

  // Unique global callback for the YouTube iframe API
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
    var playerIframe = block.querySelector(".sync-player");
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
          // Force OSMD a rendre sur UNE seule ligne horizontale : on
          // elargit temporairement osmd-host a 20000px avant render, ce
          // qui donne a OSMD une largeur de page virtuellement infinie
          // et l'empeche de replier sur plusieurs systemes. Ensuite on
          // recale la largeur sur celle du SVG reellement rendu.
          osmdDiv.style.width = "20000px";
          osmd.render();
          var svg = osmdDiv.querySelector("svg");
          if (svg) {
            osmdDiv.style.width = Math.ceil(svg.getBoundingClientRect().width) + "px";
          } else {
            osmdDiv.style.width = "";
          }
          osmd.cursor.show();
          forceCursorImgSize(osmdDiv);
          fitHeights(block, osmdDiv);

          // Compte les steps reels du curseur OSMD pour aligner notre
          // timemap dessus. Si MuseScore a plus ou moins de "beat
          // positions" dans le MusicXML que nos onsets MIDI, la sync
          // derive : on resample notre timemap sur la bonne longueur.
          var osmdSteps = countCursorSteps(osmd);
          var origLen = state.timemap.length;
          if (osmdSteps > 0 && osmdSteps !== origLen) {
            state.timemap = resampleTimemap(state.timemap, osmdSteps);
          }
          statusEl.textContent =
            "Partition OK (MIDI=" + origLen + " / OSMD=" + osmdSteps + " steps).";

          if (cursorCheckbox) {
            cursorCheckbox.addEventListener("change", function () {
              if (cursorCheckbox.checked) { osmd.cursor.show(); forceCursorImgSize(osmdDiv); }
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

  // Parcourt le curseur OSMD d'un bout a l'autre pour compter les
  // positions ("steps"). Restaure le curseur au debut a la fin.
  function countCursorSteps(osmd) {
    try {
      osmd.cursor.reset();
      var n = 0;
      var guard = 0;
      while (!osmd.cursor.iterator.EndReached && guard < 100000) {
        osmd.cursor.next();
        n++;
        guard++;
      }
      osmd.cursor.reset();
      return n;
    } catch (e) {
      console.error("countCursorSteps failed:", e);
      return 0;
    }
  }

  // Resample un tableau de temps (sec) a une longueur cible via
  // interpolation lineaire. Preserve la forme (debut/fin/intermediaires)
  // mais lisse les variations rythmiques fines.
  function resampleTimemap(src, targetLen) {
    if (targetLen <= 1 || src.length < 2) return src.slice(0, targetLen);
    var out = new Array(targetLen);
    var srcMax = src.length - 1;
    for (var i = 0; i < targetLen; i++) {
      var pos = (i / (targetLen - 1)) * srcMax;
      var lo = Math.floor(pos);
      var hi = Math.min(lo + 1, srcMax);
      var frac = pos - lo;
      out[i] = src[lo] * (1 - frac) + src[hi] * frac;
    }
    return out;
  }

  // OSMD draws the cursor as a small <img> (typically 30x1 px canvas)
  // whose rendered height is controlled via the HTML `height` attribute.
  // Just-the-Docs applies `img { height: auto }` which overrides that
  // attribute, collapsing the cursor to 1px and making it invisible.
  // Promote the attribute to an inline style, which beats the theme CSS.
  function forceCursorImgSize(osmdDiv) {
    var imgs = osmdDiv.querySelectorAll("img");
    for (var i = 0; i < imgs.length; i++) {
      var img = imgs[i];
      var h = img.getAttribute("height");
      var w = img.getAttribute("width");
      if (h) img.style.setProperty("height", h + "px", "important");
      if (w) img.style.setProperty("width", w + "px", "important");
      img.style.setProperty("max-width", "none", "important");
    }
  }

  // La hauteur de la partition = hauteur d'UN systeme complet
  // reellement rendu par OSMD (forcee en ligne unique via wide container
  // dans initBlock). La video est calee sur cette meme hauteur ; sa
  // largeur se deduit du ratio 16:9.
  function fitHeights(block, osmdDiv) {
    var scoreWrap = block.querySelector(".score-wrap");
    var videoWrap = block.querySelector(".video-wrap");
    var layout = block.querySelector(".sync-layout");
    if (!scoreWrap || !videoWrap || !layout) return;

    // Mobile (flex-direction: column via media query) : ne touche pas a
    // la largeur, fixe une hauteur plus grande pour la partition.
    if (getComputedStyle(layout).flexDirection === "column") {
      scoreWrap.style.height = "48vh";
      videoWrap.style.height = "";
      videoWrap.style.width = "";
      return;
    }

    var svg = osmdDiv.querySelector("svg");
    var systemH = svg ? svg.getBoundingClientRect().height : 260;
    // Bornes : ni trop petit (video devient illisible), ni plus grand
    // que ~55vh pour garder la suite de la page visible.
    var target = Math.max(180, Math.min(systemH + 8, window.innerHeight * 0.55, 460));
    var videoW = target * 16 / 9;

    scoreWrap.style.height = target + "px";
    videoWrap.style.height = target + "px";
    videoWrap.style.width = videoW + "px";
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

    // Scrub backward -> rewind cursor from scratch
    if (state.cursorStep > 0 && state.timemap[state.cursorStep - 1] > t + 0.25) {
      resetCursorTo(state, t);
    } else {
      while (state.cursorStep < state.timemap.length && state.timemap[state.cursorStep] <= t) {
        state.osmd.cursor.next();
        state.cursorStep++;
      }
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
