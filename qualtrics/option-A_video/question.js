/*
 * Slow-paced breathing video: gate, protect, and log.
 * Paste into the question's JavaScript editor (replace the default stub).
 *
 * What it does
 *  - Hides Next until the video has played to the end.
 *  - Starts playback from a button press (a user gesture), so sound is allowed.
 *  - Blocks skipping ahead: any forward seek is snapped back.
 *  - Pauses when the participant switches tab or minimises the window, and asks
 *    them to press "Continue" when they return, so everyone gets the full exercise on screen.
 *  - Writes compliance data to Embedded Data (see LOGGED FIELDS below).
 *
 * Before launch: set CONFIG.videoUrl, add the Embedded Data fields to the Survey Flow
 * ABOVE this block, and test in Preview on Chrome, Safari, Firefox, and Edge.
 */
Qualtrics.SurveyEngine.addOnload(function () {
  var q = this;

  var CONFIG = {
    videoUrl: "https://YOUR-HOST.example/pacer_circle_4-6_full_session_silent.mp4",
    pauseWhenHidden: true,       // pause on tab switch; resume on button press
    minWatchedFraction: 0.98,    // share of the video that must actually play for "completed = 1"
    allowAdvanceOnError: true,   // if the video can't load, let them continue (flagged in data)
    blockSmallScreens: true,     // phones are excluded; also screen with Survey Flow device logic
    minViewportWidth: 800,
    edPrefix: "spb_"
  };

  /* LOGGED FIELDS (all strings). Create each in Survey Flow as Embedded Data.
   *   New survey-taking experience: name them __js_spb_start_iso, __js_spb_completed, ...
   *   Legacy experience: name them spb_start_iso, spb_completed, ...
   *
   *   start_iso, end_iso      ISO timestamps of Start press and video end
   *   wall_s                  seconds from Start to end (should be about the video length + hidden time)
   *   media_s                 video duration reported by the browser
   *   watched_s               seconds actually played (sum of forward progress, excluding seeks)
   *   hidden_n, hidden_s      number and total length of tab-hidden episodes
   *   pauses_n                pauses not caused by tab switching (e.g., headphone unplug, OS media keys)
   *   stalls_n, stall_s       buffering interruptions and their total length
   *   seek_blocked_n          forward-seek attempts that were snapped back
   *   completed               1 if the video ended and watched_s >= minWatchedFraction * media_s
   *   error                   media error code/message, if any
   *   viewport, ua            window size and browser string at Start
   */

  var ed = function (k, v) {
    var key = CONFIG.edPrefix + k, val = String(v);
    try { if (Qualtrics.SurveyEngine.setJSEmbeddedData) Qualtrics.SurveyEngine.setJSEmbeddedData(key, val); } catch (e) {}
    try { Qualtrics.SurveyEngine.setEmbeddedData(key, val); } catch (e) {}
  };

  var root = this.getQuestionContainer();
  var video = root.querySelector("#spb-video");
  var startBtn = root.querySelector("#spb-start");
  var resumeBtn = root.querySelector("#spb-resume");
  var status = root.querySelector("#spb-status");
  var intro = root.querySelector("#spb-intro");

  q.hideNextButton();

  if (CONFIG.blockSmallScreens && window.innerWidth < CONFIG.minViewportWidth) {
    startBtn.style.display = "none";
    status.textContent = "This exercise needs a laptop or desktop screen. Please reopen the survey link on a computer.";
    ed("error", "small_viewport_" + window.innerWidth);
    return;
  }

  video.src = CONFIG.videoUrl;
  video.controls = false;
  video.disableRemotePlayback = true;
  video.addEventListener("contextmenu", function (e) { e.preventDefault(); });

  var S = {
    started: false, ended: false, tStart: 0,
    maxReached: 0, lastTime: 0, watched: 0,
    hiddenN: 0, hiddenS: 0, hiddenAt: 0, pausedByUs: false,
    pausesN: 0, stallsN: 0, stallS: 0, stallAt: 0, seekBlocked: 0
  };
  var now = function () { return performance.now() / 1000; };

  function flush() {
    ed("hidden_n", S.hiddenN); ed("hidden_s", S.hiddenS.toFixed(1));
    ed("pauses_n", S.pausesN); ed("stalls_n", S.stallsN); ed("stall_s", S.stallS.toFixed(1));
    ed("seek_blocked_n", S.seekBlocked); ed("watched_s", S.watched.toFixed(1));
  }

  startBtn.addEventListener("click", function () {
    startBtn.style.display = "none";
    intro.style.display = "none";
    video.style.display = "block";
    status.textContent = "";
    S.started = true; S.tStart = now();
    ed("start_iso", new Date().toISOString());
    ed("viewport", window.innerWidth + "x" + window.innerHeight);
    ed("ua", navigator.userAgent);
    ed("completed", 0);
    var p = video.play();
    if (p && p.catch) p.catch(function (err) {
      // Very rare after a click; offer a second press rather than failing silently.
      resumeBtn.style.display = "inline-block";
      status.textContent = "Press Continue to start the video.";
      ed("error", "play_rejected_" + (err && err.name));
    });
  });

  resumeBtn.addEventListener("click", function () {
    resumeBtn.style.display = "none"; status.textContent = "";
    S.pausedByUs = false;
    video.play();
  });

  // Count only forward progress made by normal playback; snap back any skip-ahead.
  video.addEventListener("timeupdate", function () {
    var t = video.currentTime, d = t - S.lastTime;
    if (d > 0 && d < 1.5) { S.watched += d; S.maxReached = Math.max(S.maxReached, t); }
    S.lastTime = t;
  });
  video.addEventListener("seeking", function () {
    if (video.currentTime > S.maxReached + 1) {
      S.seekBlocked++; video.currentTime = S.maxReached; S.lastTime = S.maxReached;
    }
  });

  video.addEventListener("pause", function () {
    if (S.ended || video.ended) return;
    if (!S.pausedByUs) {
      S.pausesN++;
      resumeBtn.style.display = "inline-block";
      status.textContent = "The exercise was paused. Press Continue to carry on.";
    }
  });

  video.addEventListener("waiting", function () { S.stallsN++; S.stallAt = now(); });
  video.addEventListener("playing", function () {
    if (S.stallAt) { S.stallS += now() - S.stallAt; S.stallAt = 0; }
  });

  function onVisibility() {
    if (!S.started || S.ended) return;
    if (document.hidden) {
      S.hiddenN++; S.hiddenAt = now();
      if (CONFIG.pauseWhenHidden && !video.paused) { S.pausedByUs = true; video.pause(); }
    } else if (S.hiddenAt) {
      S.hiddenS += now() - S.hiddenAt; S.hiddenAt = 0;
      if (S.pausedByUs) {
        resumeBtn.style.display = "inline-block";
        status.textContent = "Welcome back. Press Continue to pick up where you left off.";
      }
    }
    flush();
  }
  document.addEventListener("visibilitychange", onVisibility);

  video.addEventListener("ended", function () {
    S.ended = true;
    var media = isFinite(video.duration) ? video.duration : 0;
    ed("end_iso", new Date().toISOString());
    ed("wall_s", (now() - S.tStart).toFixed(1));
    ed("media_s", media.toFixed(1));
    flush();
    ed("completed", (media > 0 && S.watched >= CONFIG.minWatchedFraction * media) ? 1 : 0);
    video.style.display = "none";
    status.textContent = "Thank you. Please press the arrow to continue.";
    q.showNextButton();
  });

  video.addEventListener("error", function () {
    var err = video.error;
    ed("error", err ? ("media_" + err.code + "_" + (err.message || "")) : "media_unknown");
    status.textContent = "The video couldn't load. Please check your connection and reload the page.";
    if (CONFIG.allowAdvanceOnError) {
      status.textContent += " If it still doesn't work, press the arrow to continue.";
      q.showNextButton();
    }
  });

  Qualtrics.SurveyEngine.addOnUnload(function () {
    document.removeEventListener("visibilitychange", onVisibility);
    if (S.started && !S.ended) flush();
  });
});
