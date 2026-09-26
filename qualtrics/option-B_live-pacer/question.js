/*
 * Live slow-paced breathing pacer (no video file).
 * Same timing model and look as render_pacer.py: 4.0 s in, 6.0 s out, raised-cosine easing, no holds.
 *
 * Timing is computed from performance.now(), never from frame counts, so the breath rate is exact on
 * any refresh rate. Browsers stop animating hidden tabs, so the session clock pauses while the tab is
 * hidden and resumes on a button press: every participant gets the full 10 minutes on screen.
 *
 * Paste into the question's JavaScript editor. Add Embedded Data fields to the Survey Flow ABOVE this
 * block (new experience: __js_spb_...; legacy: spb_...). Test in Preview on each browser.
 */
Qualtrics.SurveyEngine.addOnload(function () {
  var q = this;

  var CONFIG = {
    inhaleS: 4.0, exhaleS: 6.0,
    practiceCycles: 3,             // labelled "Breathe in / Breathe out"
    pacingCycles: 60,              // 10:00 at 6 breaths per minute
    reminderAtCycles: [18, 36],    // 0-based pacing cycles starting at 3:00 and 6:00
    reminderText: "Keep breathing gently with the circle",
    endHoldS: 8,
    minViewportWidth: 800,
    edPrefix: "spb_"
  };
  var COL = { slate: "#1F2A33", guide: "#3A4A56", breath: "#86AEC2", ink: "#D8E0E4" };
  var CYCLE = CONFIG.inhaleS + CONFIG.exhaleS;
  var PRACTICE_S = CONFIG.practiceCycles * CYCLE;
  var TOTAL_S = PRACTICE_S + CONFIG.pacingCycles * CYCLE;

  /* LOGGED FIELDS
   *   start_iso, end_iso     ISO timestamps
   *   session_s              seconds of pacer time delivered (should equal 630 for 3 + 60 cycles)
   *   wall_s                 real seconds from Start to end (session + hidden time)
   *   hidden_n, hidden_s     tab-hidden episodes and their total length
   *   long_frames_n          frames that took > 100 ms (visible stutter; timing stays exact)
   *   refresh_hz             estimated display refresh rate
   *   viewport, ua           window size and browser string
   *   completed              1 when all cycles were delivered
   */
  var ed = function (k, v) {
    var key = CONFIG.edPrefix + k, val = String(v);
    try { if (Qualtrics.SurveyEngine.setJSEmbeddedData) Qualtrics.SurveyEngine.setJSEmbeddedData(key, val); } catch (e) {}
    try { Qualtrics.SurveyEngine.setEmbeddedData(key, val); } catch (e) {}
  };

  var root = this.getQuestionContainer();
  var canvas = root.querySelector("#spb-canvas");
  var startBtn = root.querySelector("#spb-start");
  var resumeBtn = root.querySelector("#spb-resume");
  var status = root.querySelector("#spb-status");
  var intro = root.querySelector("#spb-intro");
  var ctx = canvas.getContext("2d");

  q.hideNextButton();
  if (window.innerWidth < CONFIG.minViewportWidth) {
    startBtn.style.display = "none";
    status.textContent = "This exercise needs a laptop or desktop screen. Please reopen the survey link on a computer.";
    ed("error", "small_viewport_" + window.innerWidth);
    return;
  }

  // ---- timing model ----
  function ease(x) { return 0.5 - 0.5 * Math.cos(Math.PI * x); }
  function phaseAt(t) {
    var k = t % CYCLE;
    if (k < CONFIG.inhaleS) return { p: ease(k / CONFIG.inhaleS), phase: "in" };
    return { p: 1 - ease((k - CONFIG.inhaleS) / CONFIG.exhaleS), phase: "out" };
  }

  // ---- drawing (1280 x 720 design space, same geometry as the videos) ----
  var CX = 640, CY = 330, RMIN = 100, RMAX = 265;
  function fit() {
    var dpr = window.devicePixelRatio || 1, r = canvas.getBoundingClientRect();
    var w = Math.round(r.width * dpr), h = Math.round(r.height * dpr);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  }
  function text(str, size, y, alpha) {
    ctx.globalAlpha = alpha; ctx.fillStyle = COL.ink;
    ctx.font = size + "px 'Atkinson Hyperlegible', system-ui, -apple-system, 'Segoe UI', sans-serif";
    ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(str, CX, y); ctx.globalAlpha = 1;
  }
  function draw(t) {
    fit();
    var k = canvas.width / 1280;
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = COL.slate; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(k, 0, 0, k, 0, 0);
    ctx.strokeStyle = COL.guide; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(CX, CY, RMAX, 0, 2 * Math.PI); ctx.stroke();

    var s = t < TOTAL_S ? phaseAt(t) : { p: 0, phase: "in" };
    ctx.fillStyle = COL.breath; ctx.beginPath(); ctx.arc(CX, CY, RMIN + s.p * (RMAX - RMIN), 0, 2 * Math.PI); ctx.fill();

    if (t < PRACTICE_S) {
      text(s.phase === "in" ? "Breathe in" : "Breathe out", 34, 668, 1);
    } else if (t < TOTAL_S) {
      var c = Math.floor((t - PRACTICE_S) / CYCLE), into = (t - PRACTICE_S) % CYCLE;
      if (CONFIG.reminderAtCycles.indexOf(c) !== -1) text(CONFIG.reminderText, 30, 668, Math.max(0, Math.min(1, into, CYCLE - into)));
    } else {
      text("You can return to your normal breathing.", 34, 668, Math.min(1, (t - TOTAL_S) / 0.5));
    }
  }

  // ---- session clock (pauses while hidden) ----
  var S = { running: false, done: false, t0: 0, pausedAt: 0, pausedTotal: 0, wallStart: 0,
            hiddenN: 0, hiddenS: 0, hiddenAt: 0, longFrames: 0, lastFrame: 0, frameGaps: [] };
  var now = function () { return performance.now() / 1000; };
  var sessionT = function () { return (S.running ? now() : S.pausedAt) - S.t0 - S.pausedTotal; };

  function loop() {
    var n = now();
    if (S.lastFrame) {
      var gap = n - S.lastFrame;
      if (gap > 0.1) S.longFrames++;
      if (S.frameGaps.length < 120) S.frameGaps.push(gap);
    }
    S.lastFrame = n;
    var t = sessionT();
    draw(t);
    if (!S.done && t >= TOTAL_S) finish();
    if (S.done && t >= TOTAL_S + CONFIG.endHoldS) { end(); return; }
    if (S.running) requestAnimationFrame(loop);
  }
  function finish() { S.done = true; ed("session_s", sessionT().toFixed(1)); }
  function end() {
    S.running = false;
    var gaps = S.frameGaps.slice(10).sort(function (a, b) { return a - b; });
    var med = gaps.length ? gaps[Math.floor(gaps.length / 2)] : 0;
    ed("end_iso", new Date().toISOString());
    ed("wall_s", (now() - S.wallStart).toFixed(1));
    ed("hidden_n", S.hiddenN); ed("hidden_s", S.hiddenS.toFixed(1));
    ed("long_frames_n", S.longFrames); ed("refresh_hz", med ? Math.round(1 / med) : "");
    ed("completed", 1);
    canvas.style.display = "none";
    status.textContent = "The breathing exercise is complete. Please press the arrow to continue.";
    q.showNextButton();
  }

  startBtn.addEventListener("click", function () {
    startBtn.style.display = "none"; intro.style.display = "none"; canvas.style.display = "block";
    S.t0 = now(); S.wallStart = S.t0; S.running = true;
    ed("start_iso", new Date().toISOString()); ed("completed", 0);
    ed("viewport", window.innerWidth + "x" + window.innerHeight); ed("ua", navigator.userAgent);
    requestAnimationFrame(loop);
  });

  resumeBtn.addEventListener("click", function () {
    resumeBtn.style.display = "none"; status.textContent = "";
    S.pausedTotal += now() - S.pausedAt; S.running = true; S.lastFrame = 0;
    requestAnimationFrame(loop);
  });

  function onVisibility() {
    if (!S.t0 || (S.done && !S.running)) return;
    if (document.hidden) {
      S.hiddenN++; S.hiddenAt = now();
      if (S.running) { S.running = false; S.pausedAt = now(); }
    } else if (S.hiddenAt) {
      S.hiddenS += now() - S.hiddenAt; S.hiddenAt = 0;
      resumeBtn.style.display = "inline-block";
      status.textContent = "Welcome back. Press Continue to pick up where you left off.";
      draw(sessionT());
    }
  }
  document.addEventListener("visibilitychange", onVisibility);

  Qualtrics.SurveyEngine.addOnUnload(function () {
    document.removeEventListener("visibilitychange", onVisibility);
    S.running = false;
  });
});
