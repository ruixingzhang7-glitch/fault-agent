"""Web UI for the fault root cause analysis pipeline."""

import asyncio
import json
import sys

sys.path.insert(0, "/Users/wisers/Desktop/aiops/fault_agent")

from flask import Flask, render_template_string, request, jsonify
from pipeline import FaultRootCausePipeline

app = Flask(__name__)
pipeline = FaultRootCausePipeline()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>故障根因定位系统</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
  .header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 24px 32px; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between; }
  .header h1 { font-size: 22px; color: #f8fafc; }
  .header h1 span { color: #38bdf8; }
  .header .badge { background: #ef4444; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
  .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
  .input-panel { background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 24px; border: 1px solid #334155; }
  .input-panel h2 { font-size: 16px; color: #94a3b8; margin-bottom: 16px; }
  .form-row { display: flex; gap: 16px; flex-wrap: wrap; }
  .form-group { flex: 1; min-width: 200px; }
  .form-group label { display: block; font-size: 13px; color: #64748b; margin-bottom: 6px; }
  .form-group input, .form-group select { width: 100%; background: #0f172a; border: 1px solid #475569; border-radius: 8px; padding: 10px 12px; color: #e2e8f0; font-size: 14px; }
  .form-group input:focus, .form-group select:focus { outline: none; border-color: #38bdf8; }
  .btn { background: linear-gradient(135deg, #38bdf8, #0ea5e9); color: #0f172a; border: none; padding: 12px 32px; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; margin-top: 16px; transition: transform 0.1s; }
  .btn:hover { transform: translateY(-1px); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .pipeline-flow { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 24px; padding: 16px; }
  .flow-step { background: #1e293b; border: 2px solid #334155; border-radius: 12px; padding: 16px 20px; text-align: center; min-width: 160px; transition: all 0.3s; }
  .flow-step.active { border-color: #38bdf8; background: #0c4a6e; }
  .flow-step.done { border-color: #22c55e; background: #052e16; }
  .flow-step.error { border-color: #ef4444; background: #450a0a; }
  .flow-step .icon { font-size: 24px; margin-bottom: 4px; }
  .flow-step .name { font-size: 13px; color: #94a3b8; }
  .flow-step .time { font-size: 11px; color: #64748b; margin-top: 4px; }
  .flow-arrow { color: #475569; font-size: 20px; }
  .result-area { display: none; }
  .result-area.visible { display: block; }
  .card { background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 16px; border: 1px solid #334155; }
  .card h3 { font-size: 15px; color: #38bdf8; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
  .card h3 .count { background: #334155; color: #94a3b8; padding: 2px 8px; border-radius: 8px; font-size: 11px; }
  .log-list { list-style: none; }
  .log-list li { padding: 8px 12px; border-bottom: 1px solid #1e293b; display: flex; align-items: center; gap: 12px; font-size: 13px; }
  .log-list li:last-child { border-bottom: none; }
  .log-level { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; min-width: 40px; text-align: center; }
  .log-level.ERROR { background: #7f1d1d; color: #fca5a5; }
  .log-level.WARN { background: #78350f; color: #fbbf24; }
  .log-service { color: #38bdf8; font-size: 12px; min-width: 100px; }
  .log-msg { color: #cbd5e1; flex: 1; }
  .log-count { color: #64748b; font-size: 12px; }
  .metric-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
  .metric-item { background: #0f172a; border-radius: 8px; padding: 12px; border: 1px solid #334155; }
  .metric-item .label { font-size: 12px; color: #64748b; }
  .metric-item .value { font-size: 20px; color: #f8fafc; font-weight: 600; }
  .metric-item .svc { font-size: 11px; color: #38bdf8; }
  .metric-item .value.warning { color: #fbbf24; }
  .metric-item .value.critical { color: #ef4444; }
  .alert-list { list-style: none; }
  .alert-list li { padding: 10px 12px; border-bottom: 1px solid #1e293b; display: flex; align-items: center; gap: 12px; font-size: 13px; }
  .alert-severity { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .alert-severity.P0 { background: #7f1d1d; color: #fca5a5; }
  .alert-severity.P1 { background: #78350f; color: #fbbf24; }
  .alert-severity.P2 { background: #1e3a5f; color: #7dd3fc; }
  .cause-card { background: #0f172a; border-radius: 8px; padding: 16px; margin-bottom: 12px; border: 1px solid #334155; }
  .cause-card.top { border-color: #22c55e; }
  .cause-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
  .cause-rank { background: #334155; color: #94a3b8; width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; }
  .cause-rank.rank1 { background: #22c55e; color: #052e16; }
  .cause-text { font-size: 14px; color: #f8fafc; flex: 1; }
  .confidence-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .confidence-track { background: #334155; height: 8px; border-radius: 4px; flex: 1; overflow: hidden; }
  .confidence-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
  .confidence-fill.high { background: linear-gradient(90deg, #22c55e, #4ade80); }
  .confidence-fill.medium { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
  .confidence-fill.low { background: linear-gradient(90deg, #ef4444, #f87171); }
  .confidence-val { font-size: 13px; color: #94a3b8; min-width: 40px; }
  .evidence-list { list-style: none; padding-left: 40px; }
  .evidence-list li { font-size: 12px; color: #94a3b8; padding: 2px 0; }
  .evidence-list li::before { content: "→"; color: #475569; margin-right: 6px; }
  .action-result { display: flex; gap: 16px; }
  .action-box { flex: 1; background: #0f172a; border-radius: 8px; padding: 16px; border: 1px solid #334155; }
  .action-box.executed { border-color: #22c55e; }
  .action-box.skipped { border-color: #ef4444; }
  .action-label { font-size: 12px; color: #64748b; margin-bottom: 4px; }
  .action-value { font-size: 14px; color: #f8fafc; }
  .notification-box { background: #0f172a; border-radius: 8px; padding: 16px; border: 1px solid #334155; margin-top: 12px; }
  .notification-box h4 { font-size: 13px; color: #fbbf24; margin-bottom: 8px; }
  .notification-content { font-size: 13px; color: #cbd5e1; line-height: 1.6; white-space: pre-line; }
  .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .stat-item { background: #0f172a; border-radius: 8px; padding: 12px; text-align: center; border: 1px solid #334155; }
  .stat-item .label { font-size: 12px; color: #64748b; }
  .stat-item .value { font-size: 18px; color: #f8fafc; font-weight: 600; }
  .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #475569; border-top-color: #38bdf8; border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading-text { color: #94a3b8; font-size: 14px; display: flex; align-items: center; gap: 8px; justify-content: center; padding: 40px; }
</style>
</head>
<body>
<div class="header">
  <h1><span>&#9670;</span> 故障根因定位系统</h1>
  <div class="badge">AIOps Agent</div>
</div>

<div class="container">
  <div class="input-panel">
    <h2>故障参数配置</h2>
    <div class="form-row">
      <div class="form-group">
        <label>故障时间 (ISO8601)</label>
        <input type="text" id="fault_time" value="2025-04-01T10:00:00Z">
      </div>
      <div class="form-group">
        <label>回溯窗口 (分钟)</label>
        <input type="number" id="window_minutes" value="15" min="1" max="60">
      </div>
      <div class="form-group">
        <label>涉及服务</label>
        <input type="text" id="services" value="payment-api, order-db" placeholder="逗号分隔">
      </div>
    </div>
    <button class="btn" id="run_btn" onclick="runPipeline()">开始故障分析</button>
  </div>

  <div class="pipeline-flow" id="pipeline_flow">
    <div class="flow-step" id="step_perception">
      <div class="icon">&#128269;</div>
      <div class="name">感知 Agent</div>
      <div class="time" id="time_perception"></div>
    </div>
    <div class="flow-arrow">&#10132;</div>
    <div class="flow-step" id="step_reasoning">
      <div class="icon">&#128161;</div>
      <div class="name">推理 Agent</div>
      <div class="time" id="time_reasoning"></div>
    </div>
    <div class="flow-arrow">&#10132;</div>
    <div class="flow-step" id="step_action">
      <div class="icon">&#9889;</div>
      <div class="name">行动 Agent</div>
      <div class="time" id="time_action"></div>
    </div>
  </div>

  <div id="loading" style="display:none;">
    <div class="loading-text"><div class="spinner"></div> 正在执行故障分析...</div>
  </div>

  <div class="result-area" id="results">
    <!-- Perception -->
    <div class="card" id="perception_card">
      <h3>&#128269; 感知数据 <span class="count" id="perception_count"></span></h3>
      <div id="perception_content"></div>
    </div>

    <!-- Reasoning -->
    <div class="card" id="reasoning_card">
      <h3>&#128161; 推理结果 <span class="count" id="reasoning_count"></span></h3>
      <div id="reasoning_content"></div>
    </div>

    <!-- Action -->
    <div class="card" id="action_card">
      <h3>&#9889; 行动结果</h3>
      <div id="action_content"></div>
    </div>

    <!-- Stats -->
    <div class="card" id="stats_card">
      <h3>&#128202; 执行统计</h3>
      <div id="stats_content"></div>
    </div>
  </div>
</div>

<script>
function resetFlow() {
  document.querySelectorAll('.flow-step').forEach(s => {
    s.classList.remove('active', 'done', 'error');
  });
  document.querySelectorAll('.flow-step .time').forEach(t => t.textContent = '');
}

function setStepState(stepId, state, timeStr) {
  const el = document.getElementById(stepId);
  el.classList.remove('active', 'done', 'error');
  el.classList.add(state);
  if (timeStr) {
    document.getElementById('time_' + stepId.replace('step_', '')).textContent = timeStr;
  }
}

function isCritical(metric, value) {
  const thresholds = {
    'connection_pool_usage': 0.9, 'error_rate': 0.1, 'disk_usage_ratio': 0.9,
    'request_latency_p99': 1000, 'query_latency_avg': 500, 'replication_lag': 60,
  };
  if (thresholds[metric] !== undefined) {
    return value >= thresholds[metric] ? 'critical' : (value >= thresholds[metric] * 0.7 ? 'warning' : '');
  }
  return '';
}

async function runPipeline() {
  const btn = document.getElementById('run_btn');
  btn.disabled = true;
  btn.textContent = '分析中...';
  resetFlow();
  document.getElementById('loading').style.display = 'block';
  document.getElementById('results').classList.remove('visible');

  const faultTime = document.getElementById('fault_time').value;
  const windowMinutes = parseInt(document.getElementById('window_minutes').value);
  const services = document.getElementById('services').value.split(',').map(s => s.trim());

  try {
    const resp = await fetch('/api/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({fault_time: faultTime, window_minutes: windowMinutes, services: services})
    });
    const data = await resp.json();
    document.getElementById('loading').style.display = 'none';

    // Update flow steps
    const timings = data.agent_timings || {};
    setStepState('step_perception', 'done', timings.perception ? timings.perception.toFixed(2) + 's' : '');
    setStepState('step_reasoning', 'done', timings.reasoning ? timings.reasoning.toFixed(2) + 's' : '');
    setStepState('step_action', data.action && data.action.status === 'executed' ? 'done' : 'error',
                 timings.action ? timings.action.toFixed(2) + 's' : '');

    // Perception
    const p = data.perception;
    document.getElementById('perception_count').textContent =
      p.logs.length + ' 日志 / ' + p.metrics.length + ' 指标 / ' + p.alerts.length + ' 告警';

    let pHtml = '<ul class="log-list">';
    p.logs.forEach(l => {
      pHtml += `<li><span class="log-level ${l.level}">${l.level}</span><span class="log-service">${l.service}</span><span class="log-msg">${l.message}</span><span class="log-count">x${l.count}</span></li>`;
    });
    pHtml += '</ul>';

    pHtml += '<div class="metric-grid" style="margin-top:12px">';
    p.metrics.forEach(m => {
      const cls = isCritical(m.metric, m.value);
      pHtml += `<div class="metric-item"><div class="svc">${m.service}</div><div class="label">${m.metric}</div><div class="value ${cls}">${m.value} ${m.unit}</div></div>`;
    });
    pHtml += '</div>';

    pHtml += '<ul class="alert-list" style="margin-top:12px">';
    p.alerts.forEach(a => {
      pHtml += `<li><span class="alert-severity ${a.severity}">${a.severity}</span><span>${a.alert_name}</span><span style="color:#64748b;font-size:12px;margin-left:auto">${a.start_time}</span></li>`;
    });
    pHtml += '</ul>';

    document.getElementById('perception_content').innerHTML = pHtml;

    // Reasoning
    const r = data.reasoning;
    if (r) {
      document.getElementById('reasoning_count').textContent = r.possible_root_causes.length + ' 根因候选';
      let rHtml = '';
      r.possible_root_causes.forEach((rc, i) => {
        const isTop = i === 0;
        const confClass = rc.confidence >= 0.7 ? 'high' : (rc.confidence >= 0.5 ? 'medium' : 'low');
        rHtml += `<div class="cause-card ${isTop ? 'top' : ''}">
          <div class="cause-header">
            <span class="cause-rank ${isTop ? 'rank1' : ''}">${i+1}</span>
            <span class="cause-text">${rc.cause}</span>
          </div>
          <div class="confidence-bar">
            <div class="confidence-track"><div class="confidence-fill ${confClass}" style="width:${rc.confidence*100}%"></div></div>
            <span class="confidence-val">${rc.confidence.toFixed(2)}</span>
          </div>
          <ul class="evidence-list">${rc.evidence.map(e => '<li>' + e + '</li>').join('')}</ul>
        </div>`;
      });
      if (r.similar_past_cases.length) {
        rHtml += `<div style="margin-top:8px;font-size:12px;color:#64748b">相似历史案例: ${r.similar_past_cases.join(', ')}</div>`;
      }
      document.getElementById('reasoning_content').innerHTML = rHtml;
    }

    // Action
    const a = data.action;
    if (a) {
      let aHtml = `<div class="action-result">
        <div class="action-box ${a.status}">
          <div class="action-label">执行动作</div>
          <div class="action-value">${a.action_taken || '无 (人工介入)'}</div>
        </div>
        <div class="action-box ${a.status}">
          <div class="action-label">状态</div>
          <div class="action-value">${a.status === 'executed' ? '&#9989; 已执行' : '&#10060; 已跳过'}</div>
        </div>
        <div class="action-box">
          <div class="action-label">通知人员</div>
          <div class="action-value">${a.notified_users.join(', ')}</div>
        </div>
      </div>`;
      aHtml += `<div class="notification-box"><h4>&#128276; 钉钉/飞书通知</h4><div class="notification-content">${a.message}</div></div>`;
      document.getElementById('action_content').innerHTML = aHtml;
    }

    // Stats
    let sHtml = '<div class="stats-grid">';
    sHtml += `<div class="stat-item"><div class="label">Trace ID</div><div class="value">${data.trace_id}</div></div>`;
    sHtml += `<div class="stat-item"><div class="label">总耗时</div><div class="value">${Object.values(timings).reduce((a,b)=>a+b,0).toFixed(2)}s</div></div>`;
    sHtml += `<div class="stat-item"><div class="label">错误</div><div class="value">${data.error || '无'}</div></div>`;
    sHtml += '</div>';
    document.getElementById('stats_content').innerHTML = sHtml;

    document.getElementById('results').classList.add('visible');
  } catch (e) {
    document.getElementById('loading').style.display = 'none';
    setStepState('step_perception', 'error', '');
    setStepState('step_reasoning', 'error', '');
    setStepState('step_action', 'error', '');
    alert('分析失败: ' + e.message);
  }

  btn.disabled = false;
  btn.textContent = '开始故障分析';
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/run", methods=["POST"])
def api_run():
    params = request.get_json()
    fault_time = params.get("fault_time", "2025-04-01T10:00:00Z")
    window_minutes = params.get("window_minutes", 15)
    services = params.get("services", ["payment-api", "order-db"])

    result = asyncio.run(pipeline.run(
        fault_time=fault_time,
        window_minutes=window_minutes,
        services=services,
    ))

    return jsonify(result.model_dump())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)