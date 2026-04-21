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
    var playerEl = block.querySelector(".sync-player");
    var offsetInput = block.querySelector(".offset-input");
    var cursorCheckbox = block.querySelector(".cursor-checkbox");
    var statusEl = block.querySelector(".status");
    var debugEl = block.querySelector(".sync-debug");
    var isAudio = playerEl && playerEl.tagName === "AUDIO";

    var state = {
      block: block,
      osmd: null,
      timemap: null,
      timemapOrig: null,  // MIDI onsets avant resampling
      osmdSteps: 0,
      cursorStep: 0,
      player: null,    // objet avec .getCurrentTime()
      isAudio: isAudio,
      offsetInput: offsetInput,
      statusEl: statusEl,
      debugEl: debugEl,
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

          // Parcourt le curseur OSMD pour (1) compter les steps, (2)
          // enregistrer la position X de chaque step. Cette table permet
          // d'interpoler la position horizontale du curseur entre deux
          // onsets pour qu'il glisse continument au lieu de rester
          // fige sur une note longue (ex: ronde de 6s).
          state.timemapOrig = state.timemap;
          var walk = walkCursor(osmd, osmdDiv);
          state.osmdSteps = walk.count;
          state.cursorXs = walk.positions;
          var origLen = state.timemap.length;
          if (state.osmdSteps > 0 && state.osmdSteps !== origLen) {
            state.timemap = resampleTimemap(state.timemap, state.osmdSteps);
          }
          statusEl.textContent =
            "Partition OK (MIDI=" + origLen + " / OSMD=" + state.osmdSteps + " steps).";

          if (cursorCheckbox) {
            cursorCheckbox.addEventListener("change", function () {
              if (cursorCheckbox.checked) { osmd.cursor.show(); forceCursorImgSize(osmdDiv); }
              else osmd.cursor.hide();
            });
          }

          // Audio HTML5 : pas besoin de YouTube API, branche direct.
          // Video YouTube : attend que l'API soit chargee.
          if (state.isAudio) initAudioPlayer(block);
          else if (ytApiReady) initYtPlayer(block);
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
    state.player = new YT.Player(iframe.id, {
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

  function initAudioPlayer(block) {
    var state = block._syncState;
    if (!state) return;
    var audio = block.querySelector(".sync-player");
    // Wrappe l'element HTMLAudioElement dans un objet avec la meme API
    // (getCurrentTime) que le YT.Player, pour partager syncLoop.
    state.player = { getCurrentTime: function () { return audio.currentTime; } };
    audio.addEventListener("play", function () {
      if (!state.running) {
        state.running = true;
        requestAnimationFrame(function () { syncLoop(state); });
      }
    });
    state.statusEl.textContent += " | Audio pret.";
  }

  // Parcourt le curseur OSMD d'un bout a l'autre pour compter les
  // positions ("steps") ET pour enregistrer la position X de chaque
  // step (via offsetLeft de l'<img> curseur). Restaure le curseur au
  // debut a la fin.
  function walkCursor(osmd, osmdDiv) {
    var positions = [];
    var count = 0;
    try {
      osmd.cursor.reset();
      forceCursorImgSize(osmdDiv);
      var img = osmdDiv.querySelector("img");
      if (img) positions.push(img.offsetLeft);
      var guard = 0;
      while (!osmd.cursor.iterator.EndReached && guard < 100000) {
        osmd.cursor.next();
        count++;
        img = osmdDiv.querySelector("img");
        if (img) positions.push(img.offsetLeft);
        guard++;
      }
      osmd.cursor.reset();
      // count = nombre d'avances effectuees = nombre de transitions
      // entre positions. On a enregistre count+1 positions (depart + apres
      // chaque next). On retourne count+1 positions et count++ pour que
      // osmdSteps = nombre de positions visitables.
      return { count: count + 1, positions: positions };
    } catch (e) {
      console.error("walkCursor failed:", e);
      return { count: 0, positions: [] };
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
    if (!scoreWrap) return;

    var svg = osmdDiv.querySelector("svg");
    var systemH = svg ? svg.getBoundingClientRect().height : 260;
    var target = Math.max(180, Math.min(systemH + 8, window.innerHeight * 0.55, 460));

    var layout = block.querySelector(".sync-layout");
    var videoWrap = block.querySelector(".video-wrap");

    // Pas de layout flex (ex. page calibration en audio simple) :
    // juste la hauteur partition, rien a aligner.
    if (!layout || !videoWrap) {
      scoreWrap.style.height = target + "px";
      return;
    }

    // Mobile : flex column, partition pleine largeur sous la video
    if (getComputedStyle(layout).flexDirection === "column") {
      scoreWrap.style.height = "48vh";
      videoWrap.style.height = "";
      videoWrap.style.width = "";
      return;
    }

    // Desktop cote-a-cote : video calee sur la hauteur partition, ratio 16:9
    scoreWrap.style.height = target + "px";
    videoWrap.style.height = target + "px";
    videoWrap.style.width = (target * 16 / 9) + "px";
  }

  // Deplace le curseur OSMD horizontalement d'apres le temps ecoule
  // dans l'intervalle [timemap[step], timemap[step+1]]. Utilise les
  // positions pre-calculees dans walkCursor.
  function interpolateCursorX(state, t) {
    if (!state.cursorXs || state.cursorXs.length === 0) return;
    var step = state.cursorStep;
    var xs = state.cursorXs;
    if (step >= xs.length) return;

    var curT = state.timemap[step];
    var nextT = step + 1 < state.timemap.length ? state.timemap[step + 1] : curT;
    var curX = xs[step];
    var nextX = step + 1 < xs.length ? xs[step + 1] : curX;

    var frac = 0;
    if (nextT > curT) {
      frac = Math.max(0, Math.min(1, (t - curT) / (nextT - curT)));
    }
    var targetX = curX + (nextX - curX) * frac;

    var osmdDiv = state.osmdDiv || state.block.querySelector(".osmd-host");
    if (!osmdDiv) return;
    var img = osmdDiv.querySelector("img");
    if (!img) return;
    // Laisse style.left tel que pose par OSMD (curX) et applique le
    // delta via transform — evite les conflits avec OSMD qui repose
    // style.left a chaque cursor.next().
    img.style.transform = "translateX(" + (targetX - curX) + "px)";
  }

  function resetCursorTo(state, t) {
    state.osmd.cursor.reset();
    state.cursorStep = 0;
    // cursorStep represente la note actuellement surlignee (pas la
    // prochaine). On n'avance que quand t atteint l'onset SUIVANT.
    while (
      state.cursorStep + 1 < state.timemap.length &&
      state.timemap[state.cursorStep + 1] <= t
    ) {
      state.osmd.cursor.next();
      state.cursorStep++;
    }
  }

  function syncLoop(state) {
    if (!state.player || typeof state.player.getCurrentTime !== "function") {
      requestAnimationFrame(function () { syncLoop(state); });
      return;
    }
    var offset = parseFloat(state.offsetInput.value) || 0;
    var t = state.player.getCurrentTime() - offset;

    // Scrub backward -> rewind cursor from scratch
    if (state.cursorStep > 0 && state.timemap[state.cursorStep] > t + 0.25) {
      resetCursorTo(state, t);
    } else {
      // On n'avance QUE si l'onset suivant est atteint : le curseur
      // reste sur la note courante tant que t < timemap[cursorStep+1].
      while (
        state.cursorStep + 1 < state.timemap.length &&
        state.timemap[state.cursorStep + 1] <= t
      ) {
        state.osmd.cursor.next();
        state.cursorStep++;
      }
    }

    // Panneau de debug optionnel (ex. page de calibration).
    // Affiche step courant, temps, temps attendu, derive.
    if (state.debugEl) {
      var expectedT = state.timemap[state.cursorStep] != null
        ? state.timemap[state.cursorStep] : state.timemap[state.timemap.length - 1];
      var prevT = state.cursorStep > 0 ? state.timemap[state.cursorStep - 1] : 0;
      var drift = t - prevT;
      state.debugEl.textContent =
        "t=" + t.toFixed(3) + "s  step=" + state.cursorStep + "/" + state.timemap.length +
        "  prev_onset=" + prevT.toFixed(3) + "s  next_onset=" + expectedT.toFixed(3) + "s" +
        "  drift=" + drift.toFixed(3) + "s  offset=" + offset.toFixed(2) + "s";
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
