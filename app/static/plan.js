// 本周计划页的逻辑。
// 只做四件事：算周一、拉 /api/plan/{week_start}、画页面、生成计划。
// 字段名全部来自 docs/API.md，不发明新字段。

(function () {
  "use strict";

  const API_PLAN = "/api/plan/";
  const API_GENERATE = "/api/plan/generate";
  const API_CHECKIN = "/api/checkin";
  const API_STATS = "/api/stats/week";
  const API_EXPORT = "/api/export.md";

  const DAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
  const KIND_LABELS = { course: "课", fixed: "固定事件", task: "任务" };

  const els = {
    weekRange: document.getElementById("week-range"),
    weekNote: document.getElementById("week-note"),
    prevWeek: document.getElementById("prev-week"),
    nextWeek: document.getElementById("next-week"),
    message: document.getElementById("message"),
    loading: document.getElementById("loading-state"),
    errorBox: document.getElementById("error-state"),
    errorText: document.getElementById("error-text"),
    retry: document.getElementById("retry-button"),
    empty: document.getElementById("empty-state"),
    report: document.getElementById("report-card"),
    statScheduled: document.getElementById("stat-scheduled"),
    statUnscheduled: document.getElementById("stat-unscheduled"),
    statDays: document.getElementById("stat-days"),
    todaySection: document.getElementById("today-section"),
    todayDate: document.getElementById("today-date"),
    todayList: document.getElementById("today-list"),
    unscheduledSection: document.getElementById("unscheduled-section"),
    unscheduledList: document.getElementById("unscheduled-list"),
    weekSection: document.getElementById("week-section"),
    weekDays: document.getElementById("week-days"),
    statsSection: document.getElementById("stats-section"),
    statWeekScheduled: document.getElementById("stat-week-scheduled"),
    statWeekDone: document.getElementById("stat-week-done"),
    statWeekUnscheduled: document.getElementById("stat-week-unscheduled"),
    statWeekMinutes: document.getElementById("stat-week-minutes"),
    exportLink: document.getElementById("export-link")
  };

  // ---------------------------------------------------------------- 日期小工具
  function pad(number) {
    return String(number).padStart(2, "0");
  }

  function isoOf(date) {
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate());
  }

  function parseIso(iso) {
    const parts = iso.split("-").map(Number);
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  // 这一天所在周的周一（周一 = 1）
  function mondayOf(date) {
    const copy = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const shift = (copy.getDay() + 6) % 7; // 周日 0 → 6，周一 1 → 0
    copy.setDate(copy.getDate() - shift);
    return isoOf(copy);
  }

  function addDays(iso, days) {
    const date = parseIso(iso);
    date.setDate(date.getDate() + days);
    return isoOf(date);
  }

  // ---------------------------------------------------------------- 状态变量
  let weekStart = mondayOf(new Date());
  let latestRequest = 0; // 防止快速切周时旧请求覆盖新结果

  // 网址里带了 ?week=2026-11-16 就用它，刷新后还是这一周
  const query = new URLSearchParams(window.location.search);
  const weekFromUrl = query.get("week") || "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(weekFromUrl)) {
    weekStart = weekFromUrl;
  }

  // ---------------------------------------------------------------- 提示与三态
  function showMessage(text, isError) {
    els.message.hidden = false;
    els.message.textContent = text;
    els.message.style.color = isError ? "#b42318" : "#2c7a4b";
    els.message.style.background = isError ? "#fef3f2" : "#ecfdf3";
  }

  function showState(state) {
    els.loading.hidden = state !== "loading";
    els.empty.hidden = state !== "empty";
    els.errorBox.hidden = state !== "error";

    const hasContent = state === "content";
    els.report.hidden = !hasContent;
    els.todaySection.hidden = !hasContent;
    els.weekSection.hidden = !hasContent;
    if (!hasContent) {
      els.unscheduledSection.hidden = true;
      els.statsSection.hidden = true;
    }
  }

  function showError(text) {
    els.errorText.textContent = text;
    showState("error");
  }

  // FastAPI 的出错格式是 {"detail": "中文"}；格式不对时给一句兜底
  function toChineseDetail(data, status) {
    if (data && typeof data.detail === "string") {
      return data.detail;
    }
    return "操作失败（状态码 " + status + "），请稍后再试";
  }

  // ---------------------------------------------------------------- 打卡
  // 服务端没有"查这一周打了哪些卡"的接口（只有 PATCH /api/checkin），
  // 所以"刷新后还是已打卡"靠浏览器本地存储记住。
  // 同一台电脑、同一个浏览器有效；换浏览器会显示成未打卡。
  function checkinKey(block) {
    return "checkin:" + block.date + ":" + block.task_id;
  }

  function isChecked(block) {
    try {
      return window.localStorage.getItem(checkinKey(block)) === "1";
    } catch (error) {
      return false;
    }
  }

  function rememberChecked(block) {
    try {
      window.localStorage.setItem(checkinKey(block), "1");
    } catch (error) {
      // 浏览器禁用本地存储时忽略：本次页面仍然显示已打卡
    }
  }

  function setCheckinButtonState(button, checked) {
    button.textContent = checked ? "已打卡 ✅" : "打卡";
    button.disabled = checked;
    button.classList.toggle("is-checked", checked);
  }

  async function checkIn(block, button, item) {
    button.disabled = true;
    button.textContent = "打卡中…";

    let response;
    try {
      response = await fetch(API_CHECKIN, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: block.task_id, date: block.date })
      });
    } catch (error) {
      setCheckinButtonState(button, false);
      showMessage("连不上后台，请确认终端里还在运行 Uvicorn。", true);
      return;
    }

    if (!response.ok) {
      const data = await response.json().catch(function () { return {}; });
      setCheckinButtonState(button, false);
      showMessage(toChineseDetail(data, response.status), true);
      return;
    }

    const data = await response.json().catch(function () { return {}; });
    // created=false = 今天已经打过卡，接口幂等：照样显示已打卡，不报错
    rememberChecked(block);
    setCheckinButtonState(button, true);
    item.classList.add("checked");

    if (data.created === false) {
      showMessage("这个任务今天已经打过卡了（不会重复计数）。", false);
    } else {
      showMessage("已打卡：「" + block.title + "」", false);
    }

    // 打卡后统计的"已完成"要立刻跟着变
    loadStats();
  }

  // ---------------------------------------------------------------- 画一块时间
  function blockItem(block) {
    const item = document.createElement("div");
    item.className = "block-item";

    const time = document.createElement("span");
    time.className = "block-time";
    time.textContent = block.start + "–" + block.end;

    const title = document.createElement("span");
    title.className = "block-title";
    title.textContent = block.title;

    const badge = document.createElement("span");
    badge.className = "badge badge-" + block.kind;
    badge.textContent = KIND_LABELS[block.kind] || block.kind;

    item.appendChild(time);
    item.appendChild(title);
    item.appendChild(badge);

    // 只有任务块能打卡；课和固定事件没有 task_id
    if (block.kind === "task" && block.task_id != null) {
      const checked = isChecked(block);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "checkin-button";
      setCheckinButtonState(button, checked);

      if (checked) {
        item.classList.add("checked");
      } else {
        button.addEventListener("click", function () {
          checkIn(block, button, item);
        });
      }

      item.appendChild(button);
    }

    return item;
  }

  function emptyLine(text) {
    const p = document.createElement("p");
    p.className = "empty-day";
    p.textContent = text;
    return p;
  }

  // ---------------------------------------------------------------- 三个区块
  function renderToday(blocks, today) {
    els.todayList.replaceChildren();
    els.todayDate.textContent = today;

    const weekEnd = addDays(weekStart, 6);
    if (today < weekStart || today > weekEnd) {
      els.todayList.appendChild(emptyLine("今天不在这周里。"));
      return;
    }

    const todayBlocks = blocks
      .filter(function (block) { return block.date === today; })
      .sort(function (a, b) { return a.start < b.start ? -1 : a.start > b.start ? 1 : 0; });

    if (todayBlocks.length === 0) {
      els.todayList.appendChild(emptyLine("今天没有安排。"));
      return;
    }

    todayBlocks.forEach(function (block) {
      els.todayList.appendChild(blockItem(block));
    });
  }

  function renderUnscheduled(items) {
    if (items.length === 0) {
      els.unscheduledSection.hidden = true;
      return;
    }

    els.unscheduledList.replaceChildren();
    items.forEach(function (task) {
      const li = document.createElement("li");
      const title = document.createElement("strong");
      title.textContent = task.title;
      const reason = document.createElement("small");
      reason.textContent = "原因：" + task.reason;
      li.appendChild(title);
      li.appendChild(document.createElement("br"));
      li.appendChild(reason);
      els.unscheduledList.appendChild(li);
    });
    els.unscheduledSection.hidden = false;
  }

  function renderWeek(blocks, today) {
    els.weekDays.replaceChildren();

    for (let offset = 0; offset < 7; offset += 1) {
      const date = addDays(weekStart, offset);
      const dayBlocks = blocks
        .filter(function (block) { return block.date === date; })
        .sort(function (a, b) { return a.start < b.start ? -1 : a.start > b.start ? 1 : 0; });

      const group = document.createElement("div");
      group.className = "day-group" + (date === today ? " today" : "");

      const heading = document.createElement("h4");
      heading.textContent = DAY_NAMES[offset];
      const dateSmall = document.createElement("small");
      dateSmall.textContent = date.slice(5); // 11-16
      heading.appendChild(dateSmall);
      if (date === today) {
        const todayBadge = document.createElement("span");
        todayBadge.className = "badge badge-task";
        todayBadge.textContent = "今天";
        heading.appendChild(todayBadge);
      }
      group.appendChild(heading);

      if (dayBlocks.length === 0) {
        group.appendChild(emptyLine("没有安排"));
      } else {
        dayBlocks.forEach(function (block) {
          group.appendChild(blockItem(block));
        });
      }

      els.weekDays.appendChild(group);
    }
  }

  function renderPlan(data) {
    const stats = data.stats || {};
    const blocks = data.blocks || [];
    const today = isoOf(new Date());

    els.statScheduled.textContent = stats.scheduled == null ? 0 : stats.scheduled;
    els.statUnscheduled.textContent = stats.unscheduled == null ? 0 : stats.unscheduled;

    const daysWithBlocks = new Set(blocks.map(function (block) { return block.date; }));
    els.statDays.textContent = daysWithBlocks.size;

    renderToday(blocks, today);
    renderUnscheduled(data.unscheduled || []);
    renderWeek(blocks, today);

    // 导出链接跟着当前周走（普通 <a>，浏览器直接下载）
    els.exportLink.href = API_EXPORT + "?week_start=" + weekStart;
  }

  // ---------------------------------------------------------------- 本周统计
  let latestStatsRequest = 0;

  function formatMinutes(total) {
    const minutes = Number(total) || 0;
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;
    if (hours === 0) { return minutes + " 分钟"; }
    if (rest === 0) { return hours + " 小时"; }
    return hours + " 小时 " + rest + " 分钟";
  }

  async function loadStats() {
    const requestId = latestStatsRequest + 1;
    latestStatsRequest = requestId;
    const week = weekStart;

    els.statsSection.hidden = true;

    let response;
    try {
      response = await fetch(API_STATS + "?week_start=" + week);
    } catch (error) {
      if (requestId !== latestStatsRequest) { return; }
      showMessage("统计加载失败：连不上后台。", true);
      return;
    }
    if (requestId !== latestStatsRequest || week !== weekStart) { return; }

    if (!response.ok) {
      const data = await response.json().catch(function () { return {}; });
      // 404 = 这一周没有计划，属于正常状态，不弹红字
      if (response.status !== 404) {
        showMessage(toChineseDetail(data, response.status), true);
      }
      return;
    }

    const data = await response.json();
    if (requestId !== latestStatsRequest || week !== weekStart) { return; }

    const totals = data.totals || {};
    els.statWeekScheduled.textContent = totals.scheduled == null ? 0 : totals.scheduled;
    els.statWeekDone.textContent = totals.done == null ? 0 : totals.done;
    els.statWeekUnscheduled.textContent = totals.unscheduled == null ? 0 : totals.unscheduled;
    els.statWeekMinutes.textContent = formatMinutes(totals.planned_minutes);

    els.statsSection.hidden = false;
  }

  // ---------------------------------------------------------------- 拉数据
  function updateWeekLabel() {
    const start = parseIso(weekStart);
    const end = parseIso(addDays(weekStart, 6));
    els.weekRange.textContent =
      (start.getMonth() + 1) + "月" + start.getDate() + "日 – " +
      (end.getMonth() + 1) + "月" + end.getDate() + "日";

    const thisMonday = mondayOf(new Date());
    if (weekStart === thisMonday) {
      els.weekNote.textContent = "本周";
    } else if (weekStart < thisMonday) {
      els.weekNote.textContent = "过去的周";
    } else {
      els.weekNote.textContent = "未来的周";
    }
  }

  function syncUrl() {
    // 用 replaceState：换周不刷新页面，但网址会变，刷新后还能回到这一周
    window.history.replaceState(null, "", "?week=" + weekStart);
  }

  async function loadPlan() {
    const requestId = latestRequest + 1;
    latestRequest = requestId;

    showState("loading");

    let response;
    try {
      response = await fetch(API_PLAN + weekStart);
    } catch (error) {
      if (requestId !== latestRequest) { return; }
      showError("连不上后台。请确认终端里还在运行 Uvicorn。");
      return;
    }
    if (requestId !== latestRequest) { return; }

    // 404 = 这一周还没生成过计划，这是正常的“空状态”
    if (response.status === 404) {
      showState("empty");
      return;
    }

    if (!response.ok) {
      const data = await response.json().catch(function () { return {}; });
      showError(toChineseDetail(data, response.status));
      return;
    }

    const data = await response.json();
    if (requestId !== latestRequest) { return; }

    renderPlan(data);
    showState("content");
    loadStats();
  }

  // ---------------------------------------------------------------- 生成计划
  function setGenerateBusy(isBusy) {
    const buttons = document.querySelectorAll(".generate-button");
    buttons.forEach(function (button) {
      button.disabled = isBusy;
    });
  }

  async function generatePlan() {
    setGenerateBusy(true);
    showMessage("正在生成，请稍等…", false);

    let response;
    try {
      response = await fetch(API_GENERATE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ week_start: weekStart })
      });
    } catch (error) {
      setGenerateBusy(false);
      showMessage("连不上后台，页面上的旧计划没有变动。", true);
      return;
    }

    if (response.status === 201) {
      showMessage("已生成本周计划。", false);
      await loadPlan();
    } else {
      const data = await response.json().catch(function () { return {}; });
      // 错误回滚：旧计划原样留在页面上，只多一条红色提示
      showMessage(toChineseDetail(data, response.status), true);
    }

    setGenerateBusy(false);
  }

  // ---------------------------------------------------------------- 绑定按钮
  function shiftWeek(days) {
    weekStart = addDays(weekStart, days);
    syncUrl();
    updateWeekLabel();
    loadPlan();
  }

  els.prevWeek.addEventListener("click", function () { shiftWeek(-7); });
  els.nextWeek.addEventListener("click", function () { shiftWeek(7); });
  els.retry.addEventListener("click", function () { loadPlan(); });
  document.querySelectorAll(".generate-button").forEach(function (button) {
    button.addEventListener("click", generatePlan);
  });

  // ---------------------------------------------------------------- 启动
  updateWeekLabel();
  loadPlan();
})();
