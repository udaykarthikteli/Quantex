/**
 * Quantex Quantum Fleet Optimization Engine - Interactive Client App
 * Three.js 3D Quantum Space Background + Leaflet Maps + Chart.js Telemetry
 */

let mapInstance = null;
let routePolylines = [];
let markerLayerGroup = null;
let currentOptimizationData = null;
let convergenceChart = null;
let basisStateChart = null;
let benchmarkChart = null;

// Transit Playback State
let playbackTimer = null;
let isPlaying = false;
let playbackStep = 0;
let animatedVehicleMarkers = [];

// Palette for vehicles
const VEHICLE_COLORS = ["#8B5CF6", "#06B6D4", "#10B981", "#EC4899", "#F59E0B"];

document.addEventListener("DOMContentLoaded", async () => {
  try {
    initThreeJSBackground();
    initLeafletMap();
    initTabs();
    await loadPresets();
    setupEventListeners();
    await runOptimization(); // Initial run after presets are loaded
  } catch (err) {
    console.error("Initialization error:", err);
  }
});

// ----------------- TOAST NOTIFICATION SYSTEM -----------------
function showNotification(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.style.cssText = "position:fixed; top:20px; right:20px; z-index:9999; display:flex; flex-direction:column; gap:10px;";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  const bg = type === "success" ? "#10B981" : type === "warning" ? "#F59E0B" : type === "error" ? "#EF4444" : "#8B5CF6";
  toast.style.cssText = `background:${bg}; color:white; padding:12px 20px; border-radius:10px; font-weight:600; font-size:13px; box-shadow:0 8px 24px rgba(0,0,0,0.4); backdrop-filter:blur(8px); transition:all 0.3s ease; opacity:0; transform:translateY(-10px);`;
  toast.textContent = message;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
  }, 50);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-10px)";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ----------------- 1. THREE.JS 3D QUANTUM BACKGROUND -----------------
function initThreeJSBackground() {
  const container = document.getElementById("quantum-canvas-container");
  if (!container) return;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.z = 45;

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const spheresGroup = new THREE.Group();
  scene.add(spheresGroup);

  const sphereGeo = new THREE.SphereGeometry(1.4, 24, 24);
  const ringGeo = new THREE.RingGeometry(2.2, 2.35, 32);

  const numBlochSpheres = 12;
  const blochNodes = [];

  for (let i = 0; i < numBlochSpheres; i++) {
    const material = new THREE.MeshBasicMaterial({
      color: i % 2 === 0 ? 0x8b5cf6 : 0x06b6d4,
      wireframe: true,
      transparent: true,
      opacity: 0.35
    });

    const mesh = new THREE.Mesh(sphereGeo, material);
    mesh.position.set(
      (Math.random() - 0.5) * 80,
      (Math.random() - 0.5) * 50,
      (Math.random() - 0.5) * 40
    );

    const ringMat = new THREE.MeshBasicMaterial({
      color: 0xec4899,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.25
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    mesh.add(ringMesh);

    spheresGroup.add(mesh);
    blochNodes.push({
      mesh,
      rotX: (Math.random() - 0.5) * 0.015,
      rotY: (Math.random() - 0.5) * 0.015,
      vy: (Math.random() - 0.5) * 0.02
    });
  }

  const particleCount = 200;
  const posArray = new Float32Array(particleCount * 3);

  for (let i = 0; i < particleCount * 3; i++) {
    posArray[i] = (Math.random() - 0.5) * 100;
  }

  const particleGeo = new THREE.BufferGeometry();
  particleGeo.setAttribute("position", new THREE.BufferAttribute(posArray, 3));

  const particleMat = new THREE.PointsMaterial({
    size: 0.7,
    color: 0xa78bfa,
    transparent: true,
    opacity: 0.6
  });

  const particleSystem = new THREE.Points(particleGeo, particleMat);
  scene.add(particleSystem);

  let mouseX = 0;
  let mouseY = 0;
  window.addEventListener("mousemove", (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 4;
    mouseY = (e.clientY / window.innerHeight - 0.5) * 4;
  });

  window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  function animate() {
    requestAnimationFrame(animate);

    blochNodes.forEach((node) => {
      node.mesh.rotation.x += node.rotX;
      node.mesh.rotation.y += node.rotY;
      node.mesh.position.y += node.vy;
      if (Math.abs(node.mesh.position.y) > 30) node.vy *= -1;
    });

    particleSystem.rotation.y += 0.0008;

    spheresGroup.rotation.y = THREE.MathUtils.lerp(spheresGroup.rotation.y, mouseX * 0.2, 0.05);
    spheresGroup.rotation.x = THREE.MathUtils.lerp(spheresGroup.rotation.x, mouseY * 0.2, 0.05);

    renderer.render(scene, camera);
  }

  animate();
}

// ----------------- 2. LEAFLET MAP INITIALIZATION -----------------
function initLeafletMap() {
  const mapElement = document.getElementById("map");
  if (!mapElement) return;

  mapInstance = L.map("map", { zoomControl: true }).setView([17.7215, 83.3060], 13);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 19
  }).addTo(mapInstance);

  markerLayerGroup = L.layerGroup().addTo(mapInstance);

  // Invalidate map size to prevent gray tiles
  setTimeout(() => {
    mapInstance.invalidateSize();
  }, 300);
}

// ----------------- 3. TAB CONTROLLER -----------------
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");

      if (targetId === "tab-map" && mapInstance) {
        setTimeout(() => mapInstance.invalidateSize(), 150);
      }
    });
  });
}

// ----------------- 4. PRESETS LOADER -----------------
async function loadPresets() {
  try {
    const res = await fetch("/api/presets");
    const presets = await res.json();
    const select = document.getElementById("preset-select");
    select.innerHTML = "";

    Object.keys(presets).forEach((key) => {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = `${key} (${presets[key].num_nodes} stops, ${presets[key].num_vehicles} vehicles)`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error("Failed to load presets", err);
    showNotification("Failed to connect to backend API.", "error");
  }
}

// ----------------- 5. QUANTUM OPTIMIZATION CALL -----------------
async function runOptimization() {
  const btn = document.getElementById("run-optimize-btn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Optimizing Quantum Circuit...`;
  }

  const presetSelect = document.getElementById("preset-select");
  const presetName = presetSelect && presetSelect.value ? presetSelect.value : "E-Commerce Last-Mile Express";
  const solverType = document.getElementById("solver-select").value || "qaoa";
  const qaoaReps = parseInt(document.getElementById("reps-slider").value) || 1;
  const trafficMultiplier = parseFloat(document.getElementById("traffic-slider").value) || 1.0;

  try {
    const response = await fetch("/api/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        preset_name: presetName,
        solver_type: solverType,
        qaoa_reps: qaoaReps,
        traffic_multiplier: trafficMultiplier
      })
    });

    if (!response.ok) throw new Error("Optimization failed on backend");

    const data = await response.json();
    currentOptimizationData = data;

    updateKPICards(data);
    renderMapRoutes(data);
    renderTelemetry(data);
    renderManifestTable(data);
    renderPlaybackControls(data);
    populateTrafficModalDropdowns(data);

    showNotification(`⚡ Quantum Optimization Complete via ${solverType.toUpperCase()}!`, "success");

  } catch (error) {
    console.error("Optimization failed:", error);
    showNotification("Optimization error. Ensure backend server is running.", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-atom"></i> <span>Execute Quantum Solver</span>`;
    }
  }
}

// ----------------- 6. UPDATE KPI METRIC CARDS -----------------
function updateKPICards(data) {
  const agg = data.aggregated_metrics;
  const comp = data.baseline_comparison;

  document.getElementById("kpi-dist").textContent = `${agg.distance_km.toFixed(2)} km`;
  document.getElementById("kpi-dist-delta").textContent = comp.distance_saved_km > 0 ? `-${comp.distance_saved_km} km saved` : "Optimal";

  document.getElementById("kpi-fuel").textContent = `${agg.fuel_consumed.toFixed(2)} L/kWh`;
  document.getElementById("kpi-fuel-delta").textContent = comp.fuel_saved > 0 ? `-${comp.fuel_saved} saved` : "Optimal";

  document.getElementById("kpi-co2").textContent = `${agg.co2_emissions_kg.toFixed(2)} kg`;
  document.getElementById("kpi-co2-delta").textContent = comp.co2_saved_kg > 0 ? `-${comp.co2_saved_kg} kg abated` : "Optimal";

  document.getElementById("kpi-time").textContent = `${agg.total_time_min.toFixed(1)} min`;
  document.getElementById("kpi-time-delta").textContent = comp.time_saved_min > 0 ? `-${comp.time_saved_min} min faster` : "Optimal";

  document.getElementById("kpi-cost").textContent = `$${agg.total_operational_cost.toFixed(2)}`;
  document.getElementById("kpi-cost-delta").textContent = comp.cost_saved_usd > 0 ? `-$${comp.cost_saved_usd} saved` : "Optimal";
}

// ----------------- 7. RENDER MAP & VISIBLE DEPOT -----------------
function renderMapRoutes(data) {
  if (!mapInstance || !markerLayerGroup) return;

  markerLayerGroup.clearLayers();
  routePolylines.forEach((poly) => mapInstance.removeLayer(poly));
  routePolylines = [];

  const nodes = data.nodes;
  const bounds = [];

  // 1. Visible, High-Contrast Red Depot Marker
  const depot = nodes.find((n) => n.is_depot) || nodes[0];
  const depotIcon = L.divIcon({
    className: "depot-map-marker",
    html: `
      <div style="background:#EF4444; width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:3px solid #ffffff; box-shadow:0 0 16px #ef4444; color:white; font-size:12px;">
        <i class="fa-solid fa-warehouse"></i>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  });

  L.marker([depot.lat, depot.lon], { icon: depotIcon })
    .bindPopup(`<b style="color:#EF4444; font-size:14px;"><i class="fa-solid fa-warehouse"></i> CENTRAL DEPOT</b><br>${depot.name}`)
    .addTo(markerLayerGroup);

  bounds.push([depot.lat, depot.lon]);

  // 2. Visible Customer Waypoints
  nodes.forEach((node) => {
    if (!node.is_depot) {
      const isUrgent = node.priority >= 4;
      const color = isUrgent ? "#F43F5E" : "#38BDF8";
      const icon = L.divIcon({
        className: "customer-map-marker",
        html: `
          <div style="background:${color}; width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:2px solid #ffffff; box-shadow:0 0 12px ${color}; color:white; font-size:10px;">
            ${node.id}
          </div>
        `,
        iconSize: [22, 22],
        iconAnchor: [11, 11]
      });

      L.marker([node.lat, node.lon], { icon })
        .bindPopup(`
          <div style="font-family:sans-serif; min-width:160px;">
            <b style="color:#8b5cf6; font-size:13px;">📦 Stop ${node.id}: ${node.name}</b><br>
            <b>Demand:</b> ${node.demand} kg<br>
            <b>Time Window:</b> ${node.tw_start} - ${node.tw_end} min<br>
            <b>Priority:</b> ${isUrgent ? "🔴 High / Urgent" : "🟢 Normal"}
          </div>
        `)
        .addTo(markerLayerGroup);

      bounds.push([node.lat, node.lon]);
    }
  });

  // 3. Draw Vehicle Paths with Arrows
  data.routes.forEach((route, idx) => {
    if (route.length < 2) return;
    const color = VEHICLE_COLORS[idx % VEHICLE_COLORS.length];
    const coords = route.map((nodeId) => [nodes[nodeId].lat, nodes[nodeId].lon]);
    const vehicle = data.vehicles[idx] || { name: `Vehicle ${idx + 1}`, type: "Fleet" };

    const poly = L.polyline(coords, {
      color: color,
      weight: 5,
      opacity: 0.9,
      lineJoin: "round"
    }).bindPopup(`<b>🚚 ${vehicle.name}</b> (${vehicle.type})<br>Stops: ${route.length} waypoints`);

    poly.addTo(mapInstance);
    routePolylines.push(poly);
  });

  if (bounds.length > 0) {
    mapInstance.fitBounds(bounds, { padding: [50, 50] });
  }
}

// ----------------- 8. QUANTUM TELEMETRY & CHARTS -----------------
function renderTelemetry(data) {
  const telemetry = data.telemetry;
  if (telemetry) {
    document.getElementById("tele-qubits").textContent = telemetry.num_qubits;
    document.getElementById("tele-depth").textContent = telemetry.depth;
    document.getElementById("tele-cnot").textContent = telemetry.cnot_count;
    document.getElementById("tele-params").textContent = telemetry.num_parameters;
  } else {
    document.getElementById("tele-qubits").textContent = "4";
    document.getElementById("tele-depth").textContent = "8";
    document.getElementById("tele-cnot").textContent = "6";
    document.getElementById("tele-params").textContent = "2";
  }

  // ASCII Circuit
  if (data.ascii_circuit) {
    document.getElementById("ascii-circuit-code").textContent = data.ascii_circuit;
  }

  // 1. Energy Convergence Chart
  const convCtx = document.getElementById("convergence-chart");
  if (convCtx) {
    if (convergenceChart) convergenceChart.destroy();
    const evals = (data.convergence || []).map((c) => c[0]);
    const costs = (data.convergence || []).map((c) => c[1]);

    convergenceChart = new Chart(convCtx, {
      type: "line",
      data: {
        labels: evals.length > 0 ? evals : [1, 2, 3, 4, 5],
        datasets: [{
          label: "Hamiltonian Expectation ⟨H_C⟩",
          data: costs.length > 0 ? costs : [12.4, 9.8, 7.2, 5.9, 5.4],
          borderColor: "#8B5CF6",
          backgroundColor: "rgba(139, 92, 246, 0.15)",
          fill: true,
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: "#cbd5e1" } } },
        scales: {
          x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.06)" } },
          y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.06)" } }
        }
      }
    });
  }

  // 2. Basis State Probabilities Chart
  const distCtx = document.getElementById("basis-chart");
  if (distCtx) {
    if (basisStateChart) basisStateChart.destroy();
    const states = Object.keys(data.state_distribution || {}).slice(0, 8);
    const probs = Object.values(data.state_distribution || {}).slice(0, 8);

    basisStateChart = new Chart(distCtx, {
      type: "bar",
      data: {
        labels: states.length > 0 ? states : ["|1001⟩", "|0110⟩", "|1010⟩", "|0101⟩"],
        datasets: [{
          label: "Probability P(|x⟩)",
          data: probs.length > 0 ? probs : [0.42, 0.28, 0.14, 0.08],
          backgroundColor: "#06B6D4",
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: "#cbd5e1" } } },
        scales: {
          x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.06)" } },
          y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.06)" } }
        }
      }
    });
  }
}

// ----------------- 9. LIVE FLEET PLAYBACK -----------------
function renderPlaybackControls(data) {
  const container = document.getElementById("playback-fleet-status");
  if (!container) return;

  container.innerHTML = "";
  const maxSteps = Math.max(...data.routes.map((r) => r.length));
  const slider = document.getElementById("playback-slider");
  if (slider) {
    slider.max = maxSteps;
    slider.value = 1;
  }

  updatePlaybackState(1);
}

function updatePlaybackState(step) {
  if (!currentOptimizationData) return;
  playbackStep = step;
  const data = currentOptimizationData;
  const container = document.getElementById("playback-fleet-status");
  container.innerHTML = "";

  data.routes.forEach((route, vIdx) => {
    const v = data.vehicles[vIdx] || { name: `Vehicle ${vIdx + 1}`, type: "Fleet", capacity: 50 };
    const currIdx = Math.min(step - 1, route.length - 1);
    const currNodeId = route[currIdx];
    const currNode = data.nodes[currNodeId];

    const card = document.createElement("div");
    card.className = "glass-panel";
    card.style.padding = "16px";
    card.innerHTML = `
      <h4 style="color:${VEHICLE_COLORS[vIdx % VEHICLE_COLORS.length]}; margin-bottom:6px;">🚚 ${v.name} (${v.type})</h4>
      <p style="font-size:13px; color:#cbd5e1;"><b>Current Stop:</b> ${currNode.name}</p>
      <p style="font-size:12px; color:#94a3b8;"><b>Status:</b> ${currNode.is_depot ? "🏢 At Central Depot" : "📦 Delivering Package"}</p>
      <div style="background:rgba(255,255,255,0.1); border-radius:10px; height:8px; margin-top:8px; overflow:hidden;">
        <div style="background:#8b5cf6; width:${((currIdx + 1) / route.length) * 100}%; height:100%;"></div>
      </div>
      <p style="font-size:11px; color:#94a3b8; margin-top:4px;">Progress: Stop ${currIdx + 1} of ${route.length}</p>
    `;
    container.appendChild(card);
  });
}

// ----------------- 10. BENCHMARK ARENA -----------------
async function runBenchmarkArena() {
  const presetName = document.getElementById("preset-select").value;
  const btn = document.getElementById("run-bench-btn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Running Benchmark Race...`;
  }

  try {
    const res = await fetch(`/api/benchmark?preset_name=${encodeURIComponent(presetName)}`);
    const data = await res.json();
    const bench = data.benchmark;

    const ctx = document.getElementById("arena-chart");
    if (ctx) {
      if (benchmarkChart) benchmarkChart.destroy();

      benchmarkChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels: bench.map((b) => b.name),
          datasets: [
            {
              label: "Distance (km)",
              data: bench.map((b) => b.distance_km),
              backgroundColor: bench.map((b) => b.color || "#8B5CF6"),
              borderRadius: 6
            },
            {
              label: "CO2 Emissions (kg)",
              data: bench.map((b) => b.co2_kg),
              backgroundColor: "#10B981",
              borderRadius: 6
            }
          ]
        },
        options: {
          responsive: true,
          plugins: { legend: { labels: { color: "#cbd5e1" } } },
          scales: {
            x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.06)" } },
            y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.06)" } }
          }
        }
      });
      showNotification("🏆 Multi-Solver Benchmark Complete!", "success");
    }
  } catch (err) {
    console.error("Benchmark failed:", err);
    showNotification("Benchmark execution failed.", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-bolt"></i> Run Solver Benchmark`;
    }
  }
}

// ----------------- 11. MANIFEST TABLE & CSV EXPORT -----------------
function renderManifestTable(data) {
  const tbody = document.getElementById("manifest-tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  data.fleet_sustainability.forEach((v) => {
    const routeStr = v.route.map((id) => data.nodes[id].name).join(" ➔ ");
    const tr = document.createElement("tr");
    tr.style.borderBottom = "1px solid rgba(255,255,255,0.06)";
    tr.innerHTML = `
      <td style="padding:12px; font-weight:700; color:#c4b5fd;">${v.vehicle_name}</td>
      <td style="padding:12px; color:#94a3b8;">${v.vehicle_type}</td>
      <td style="padding:12px; font-size:12px; color:#e2e8f0;">${routeStr}</td>
      <td style="padding:12px; text-align:right;">${v.distance_km.toFixed(2)} km</td>
      <td style="padding:12px; text-align:right;">${v.total_time_min.toFixed(1)} m</td>
      <td style="padding:12px; text-align:right; color:#10b981; font-weight:700;">${v.co2_emissions_kg.toFixed(2)} kg</td>
      <td style="padding:12px; text-align:right; font-weight:700;">$${v.total_operational_cost.toFixed(2)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function exportManifestCSV() {
  if (!currentOptimizationData) return;
  const data = currentOptimizationData;
  let csv = "Vehicle,Type,Distance_km,Time_min,CO2_kg,Cost_USD,Route\n";

  data.fleet_sustainability.forEach((v) => {
    const routeStr = v.route.map((id) => data.nodes[id].name).join(" -> ");
    csv += `"${v.vehicle_name}","${v.vehicle_type}",${v.distance_km},${v.total_time_min},${v.co2_emissions_kg},${v.total_operational_cost},"${routeStr}"\n`;
  });

  const blob = new Blob([csv], { type: "text/csv" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.setAttribute("href", url);
  a.setAttribute("download", "quantex_fleet_dispatch.csv");
  a.click();
  showNotification("📥 Fleet Dispatch CSV Exported!", "success");
}

function populateTrafficModalDropdowns(data) {
  const fromSelect = document.getElementById("traffic-from-node");
  const toSelect = document.getElementById("traffic-to-node");
  if (!fromSelect || !toSelect) return;

  fromSelect.innerHTML = "";
  toSelect.innerHTML = "";

  data.nodes.forEach((node) => {
    const opt1 = document.createElement("option");
    opt1.value = node.id;
    opt1.textContent = `Stop ${node.id}: ${node.name}`;
    fromSelect.appendChild(opt1);

    const opt2 = document.createElement("option");
    opt2.value = node.id;
    opt2.textContent = `Stop ${node.id}: ${node.name}`;
    toSelect.appendChild(opt2);
  });

  if (data.nodes.length > 2) {
    toSelect.selectedIndex = 2;
  }
}

// ----------------- 12. EVENT LISTENERS & MODALS -----------------
function setupEventListeners() {
  const runBtn = document.getElementById("run-optimize-btn");
  if (runBtn) runBtn.addEventListener("click", runOptimization);

  const presetSelect = document.getElementById("preset-select");
  if (presetSelect) presetSelect.addEventListener("change", runOptimization);

  const solverSelect = document.getElementById("solver-select");
  if (solverSelect) solverSelect.addEventListener("change", runOptimization);

  const exportBtn = document.getElementById("export-csv-btn");
  if (exportBtn) exportBtn.addEventListener("click", exportManifestCSV);

  // Playback slider
  const slider = document.getElementById("playback-slider");
  if (slider) {
    slider.addEventListener("input", (e) => updatePlaybackState(parseInt(e.target.value)));
  }

  // Play button
  const playBtn = document.getElementById("playback-play-btn");
  if (playBtn) {
    playBtn.addEventListener("click", () => {
      if (isPlaying) {
        clearInterval(playbackTimer);
        isPlaying = false;
        playBtn.textContent = "▶ Play";
      } else {
        isPlaying = true;
        playBtn.textContent = "⏸ Pause";
        playbackTimer = setInterval(() => {
          const max = parseInt(slider.max) || 1;
          let next = playbackStep + 1;
          if (next > max) next = 1;
          slider.value = next;
          updatePlaybackState(next);
        }, 1200);
      }
    });
  }

  // Benchmark button
  const benchBtn = document.getElementById("run-bench-btn");
  if (benchBtn) benchBtn.addEventListener("click", runBenchmarkArena);

  // Urgent Order Modal
  const orderModal = document.getElementById("order-modal");
  const openOrderBtn = document.getElementById("open-order-modal-btn");
  const closeOrderBtn = document.getElementById("close-order-modal");
  const submitOrderBtn = document.getElementById("submit-urgent-order");

  if (openOrderBtn) {
    openOrderBtn.addEventListener("click", () => {
      // Pre-fill coordinates around depot
      if (currentOptimizationData && currentOptimizationData.nodes) {
        const depot = currentOptimizationData.nodes.find((n) => n.is_depot) || currentOptimizationData.nodes[0];
        document.getElementById("order-lat").value = (depot.lat + 0.012).toFixed(4);
        document.getElementById("order-lon").value = (depot.lon + 0.008).toFixed(4);
      }
      orderModal.style.display = "flex";
    });
  }
  if (closeOrderBtn) {
    closeOrderBtn.addEventListener("click", () => {
      orderModal.style.display = "none";
    });
  }
  if (submitOrderBtn) {
    submitOrderBtn.addEventListener("click", async () => {
      submitOrderBtn.disabled = true;
      submitOrderBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Re-routing...`;

      const name = document.getElementById("order-name").value || "Emergency Delivery";
      const lat = parseFloat(document.getElementById("order-lat").value);
      const lon = parseFloat(document.getElementById("order-lon").value);
      const demand = parseFloat(document.getElementById("order-demand").value) || 2.0;

      try {
        const res = await fetch("/api/dynamic/inject-order", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, lat, lon, demand, solver_type: "qaoa" })
        });
        const data = await res.json();
        currentOptimizationData = data;
        updateKPICards(data);
        renderMapRoutes(data);
        renderManifestTable(data);
        renderPlaybackControls(data);
        orderModal.style.display = "none";
        showNotification(`⚡ Urgent Order Assigned: ${data.message}`, "success");
      } catch (err) {
        console.error(err);
        showNotification("Failed to inject urgent order.", "error");
      } finally {
        submitOrderBtn.disabled = false;
        submitOrderBtn.innerHTML = `⚡ Quantum Re-Dispatch`;
      }
    });
  }

  // Traffic Modal
  const trafficModal = document.getElementById("traffic-modal");
  const openTrafficBtn = document.getElementById("open-traffic-modal-btn");
  const closeTrafficBtn = document.getElementById("close-traffic-modal");
  const submitTrafficBtn = document.getElementById("submit-traffic-incident");

  if (openTrafficBtn) {
    openTrafficBtn.addEventListener("click", () => {
      trafficModal.style.display = "flex";
    });
  }
  if (closeTrafficBtn) {
    closeTrafficBtn.addEventListener("click", () => {
      trafficModal.style.display = "none";
    });
  }
  if (submitTrafficBtn) {
    submitTrafficBtn.addEventListener("click", async () => {
      submitTrafficBtn.disabled = true;
      submitTrafficBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Re-routing...`;

      const fromNode = parseInt(document.getElementById("traffic-from-node").value) || 0;
      const toNode = parseInt(document.getElementById("traffic-to-node").value) || 1;
      const factor = parseFloat(document.getElementById("traffic-factor").value) || 3.0;

      try {
        const res = await fetch("/api/dynamic/traffic", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ from_node: fromNode, to_node: toNode, congestion_factor: factor, solver_type: "qaoa" })
        });
        const data = await res.json();
        currentOptimizationData = data;
        updateKPICards(data);
        renderMapRoutes(data);
        renderManifestTable(data);
        renderPlaybackControls(data);
        trafficModal.style.display = "none";
        showNotification(`⚠️ Road Congestion Injected: ${data.message}`, "warning");
      } catch (err) {
        console.error(err);
        showNotification("Failed to simulate traffic incident.", "error");
      } finally {
        submitTrafficBtn.disabled = false;
        submitTrafficBtn.innerHTML = `⚠️ Re-Route Fleet`;
      }
    });
  }
}
