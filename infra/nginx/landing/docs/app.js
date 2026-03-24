/* === App Initialization === */

const panel = document.getElementById('detail-panel');
let cyArch = null;
let cyLineage = null;

// === Tab Switching ===
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
        clearPanel();

        // Lazy init graphs
        if (tab.dataset.tab === 'architecture' && !cyArch) initArchGraph();
        if (tab.dataset.tab === 'lineage' && !cyLineage) initLineageGraph();
        if (tab.dataset.tab === 'dags') renderDagList();
        if (tab.dataset.tab === 'tables') renderTableList();

        // Resize graphs
        if (cyArch) cyArch.resize();
        if (cyLineage) cyLineage.resize();
    });
});

// === Cytoscape Common Styles ===
function cyStyles() {
    return [
        { selector: 'node', style: {
            'label': 'data(label)',
            'font-family': "'JetBrains Mono', monospace",
            'font-size': '10px',
            'color': '#e8e8ec',
            'text-valign': 'center',
            'text-halign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': '100px',
            'background-color': 'data(color)',
            'border-width': 1,
            'border-color': 'rgba(255,255,255,0.1)',
            'width': 'label',
            'height': 'label',
            'padding': '14px',
            'shape': 'roundrectangle',
        }},
        { selector: 'node[type="table"]', style: {
            'shape': 'barrel',
            'background-opacity': 0.7,
            'font-size': '9px',
            'padding': '10px',
        }},
        { selector: 'node[type="topic"]', style: {
            'shape': 'hexagon',
            'background-color': '#FF6347',
            'font-size': '9px',
        }},
        { selector: 'node[type="external"]', style: {
            'shape': 'diamond',
            'background-color': '#888',
        }},
        { selector: 'edge', style: {
            'width': 1.5,
            'line-color': 'rgba(255,255,255,0.12)',
            'target-arrow-color': 'rgba(255,255,255,0.25)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.8,
        }},
        { selector: 'edge[label]', style: {
            'label': 'data(label)',
            'font-size': '8px',
            'color': 'rgba(255,255,255,0.3)',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
        }},
        { selector: '.highlighted', style: {
            'border-width': 2,
            'border-color': '#00E396',
            'background-opacity': 1,
        }},
        { selector: 'edge.highlighted', style: {
            'line-color': '#00E396',
            'target-arrow-color': '#00E396',
            'width': 2.5,
        }},
        { selector: '.dimmed', style: {
            'opacity': 0.15,
        }},
    ];
}

// === Architecture Graph ===
function initArchGraph() {
    const elements = [];

    // Service nodes
    SERVICES.forEach(s => {
        elements.push({
            data: {
                id: s.id, label: s.name,
                color: DOMAIN_COLORS[s.domain] || '#888',
                type: s.type === 'source' && s.node === 'external' ? 'external' : 'service',
                nodeGroup: s.node,
            },
        });
    });

    // Topic nodes
    TOPICS.forEach(t => {
        elements.push({
            data: { id: t.id, label: t.name, color: '#FF6347', type: 'topic' },
        });
    });

    // Edges (architecture-relevant subset)
    const archEdges = EDGES.filter(e =>
        SERVICES.some(s => s.id === e.source) || TOPICS.some(t => t.id === e.source)
    ).filter(e =>
        SERVICES.some(s => s.id === e.target) || TOPICS.some(t => t.id === e.target)
    );
    archEdges.forEach(e => {
        elements.push({ data: { source: e.source, target: e.target, label: e.label } });
    });

    cyArch = cytoscape({
        container: document.getElementById('cy-architecture'),
        elements,
        style: cyStyles(),
        layout: {
            name: 'cose',
            animate: false,
            nodeRepulsion: 8000,
            idealEdgeLength: 120,
            gravity: 0.3,
            padding: 40,
        },
        minZoom: 0.3, maxZoom: 3,
    });

    cyArch.on('tap', 'node', e => {
        const id = e.target.id();
        const svc = SERVICES.find(s => s.id === id);
        const topic = TOPICS.find(t => t.id === id);
        if (svc) showServiceDetail(svc);
        else if (topic) showTopicDetail(topic);
    });

    cyArch.on('tap', e => { if (e.target === cyArch) clearPanel(); });
}

// === Lineage Graph ===
function initLineageGraph() {
    const elements = [];
    const nodeIds = new Set();

    EDGES.forEach(e => {
        nodeIds.add(e.source);
        nodeIds.add(e.target);
    });

    nodeIds.forEach(id => {
        const svc = SERVICES.find(s => s.id === id);
        const topic = TOPICS.find(t => t.id === id);
        const tbl = TABLES.find(t => t.id === id);
        const dag = DAGS.find(d => d.id === id);

        let label, color, type;
        if (svc) { label = svc.name; color = DOMAIN_COLORS[svc.domain]; type = svc.type === 'source' && svc.node === 'external' ? 'external' : 'service'; }
        else if (topic) { label = topic.name; color = '#FF6347'; type = 'topic'; }
        else if (tbl) { label = tbl.name; color = DOMAIN_COLORS[tbl.domain]; type = 'table'; }
        else if (dag) { label = dag.name; color = DOMAIN_COLORS[dag.tags.includes('trade') ? 'trade' : dag.tags.includes('shop') ? 'shop' : 'infra']; type = 'service'; }
        else { label = id; color = '#888'; type = 'service'; }

        elements.push({ data: { id, label, color, type } });
    });

    EDGES.forEach(e => {
        elements.push({ data: { source: e.source, target: e.target, label: e.label } });
    });

    cyLineage = cytoscape({
        container: document.getElementById('cy-lineage'),
        elements,
        style: cyStyles(),
        layout: {
            name: 'dagre',
            rankDir: 'LR',
            nodeSep: 40,
            rankSep: 80,
            padding: 30,
            animate: false,
        },
        minZoom: 0.2, maxZoom: 3,
    });

    cyLineage.on('tap', 'node', e => {
        const id = e.target.id();
        highlightLineage(cyLineage, id);

        const tbl = TABLES.find(t => t.id === id);
        const svc = SERVICES.find(s => s.id === id);
        const dag = DAGS.find(d => d.id === id);
        const topic = TOPICS.find(t => t.id === id);
        if (tbl) showTableDetail(tbl);
        else if (svc) showServiceDetail(svc);
        else if (dag) showDagDetail(dag);
        else if (topic) showTopicDetail(topic);
    });

    cyLineage.on('tap', e => {
        if (e.target === cyLineage) {
            cyLineage.elements().removeClass('highlighted dimmed');
            clearPanel();
        }
    });
}

function highlightLineage(cy, nodeId) {
    cy.elements().removeClass('highlighted dimmed');

    const node = cy.getElementById(nodeId);
    const upstream = node.predecessors();
    const downstream = node.successors();
    const connected = upstream.union(downstream).union(node);

    cy.elements().addClass('dimmed');
    connected.removeClass('dimmed').addClass('highlighted');
}

// === DAG List ===
function renderDagList(filter = 'all') {
    const list = document.getElementById('dag-list');
    const filtered = filter === 'all' ? DAGS : DAGS.filter(d => d.tags.includes(filter));

    list.innerHTML = filtered.map(d => {
        const tagColor = d.tags.includes('trade') ? 'var(--accent-trade)' : d.tags.includes('shop') ? 'var(--accent-shop)' : 'var(--accent-infra)';
        return `
        <div class="dag-card" data-id="${d.id}">
            <div class="dag-card-header">
                <span class="dag-name">${d.name}</span>
                <span class="dag-schedule">${d.scheduleKr}</span>
            </div>
            <div class="dag-tags">
                ${d.tags.map(t => `<span class="dag-tag" style="background:${tagColor}22;color:${tagColor}">${t}</span>`).join('')}
                ${d.catchup ? '<span class="dag-tag" style="background:rgba(0,227,150,0.15);color:#00E396">catchup</span>' : ''}
            </div>
        </div>`;
    }).join('');

    list.querySelectorAll('.dag-card').forEach(card => {
        card.addEventListener('click', () => {
            list.querySelectorAll('.dag-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            const dag = DAGS.find(d => d.id === card.dataset.id);
            if (dag) showDagDetail(dag);
        });
    });
}

// DAG filter buttons
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderDagList(btn.dataset.filter);
    });
});

// === Table List ===
function renderTableList(query = '') {
    const list = document.getElementById('table-list');
    const filtered = query
        ? TABLES.filter(t => t.name.toLowerCase().includes(query.toLowerCase()) || t.domain.includes(query.toLowerCase()))
        : TABLES;

    list.innerHTML = filtered.map(t => {
        const color = DOMAIN_COLORS[t.domain] || '#888';
        return `
        <div class="table-row" data-id="${t.id}">
            <span class="table-domain" style="background:${color}22;color:${color}">${t.domain}</span>
            <span class="table-name">${t.name}</span>
            <span class="table-layer">${LAYER_LABELS[t.layer] || t.layer}</span>
            <span class="table-freq">${t.freq}</span>
        </div>`;
    }).join('');

    list.querySelectorAll('.table-row').forEach(row => {
        row.addEventListener('click', () => {
            list.querySelectorAll('.table-row').forEach(r => r.classList.remove('selected'));
            row.classList.add('selected');
            const tbl = TABLES.find(t => t.id === row.dataset.id);
            if (tbl) showTableDetail(tbl);
        });
    });
}

document.getElementById('table-search')?.addEventListener('input', e => renderTableList(e.target.value));

// === Detail Panel Renderers ===
function clearPanel() {
    panel.innerHTML = `<div class="detail-placeholder"><div class="detail-icon">&#8594;</div><p>Click a node or item to see details</p></div>`;
}

function showServiceDetail(s) {
    const color = DOMAIN_COLORS[s.domain] || '#888';
    const inEdges = EDGES.filter(e => e.target === s.id);
    const outEdges = EDGES.filter(e => e.source === s.id);

    panel.innerHTML = `
        <span class="detail-badge" style="background:${color}22;color:${color}">${s.domain.toUpperCase()} / ${s.type}</span>
        <div class="detail-title">${s.name}</div>
        <div class="detail-subtitle">${s.node} node</div>
        <div class="detail-desc">${s.desc}</div>
        ${s.cpu ? `<div class="detail-section">
            <div class="detail-section-title">Resources</div>
            <div class="detail-row"><span class="detail-label">CPU</span><span class="detail-value">${s.cpu}</span></div>
            <div class="detail-row"><span class="detail-label">Memory</span><span class="detail-value">${s.mem}</span></div>
        </div>` : ''}
        ${inEdges.length ? `<div class="detail-section">
            <div class="detail-section-title">Inputs (${inEdges.length})</div>
            <ul class="detail-list">${inEdges.map(e => `<li>${e.source} <span style="color:var(--text-muted)">${e.label}</span></li>`).join('')}</ul>
        </div>` : ''}
        ${outEdges.length ? `<div class="detail-section">
            <div class="detail-section-title">Outputs (${outEdges.length})</div>
            <ul class="detail-list">${outEdges.map(e => `<li>${e.target} <span style="color:var(--text-muted)">${e.label}</span></li>`).join('')}</ul>
        </div>` : ''}
    `;
}

function showDagDetail(d) {
    const color = d.tags.includes('trade') ? 'var(--accent-trade)' : d.tags.includes('shop') ? 'var(--accent-shop)' : 'var(--accent-infra)';

    panel.innerHTML = `
        <span class="detail-badge" style="background:${color.replace('var(', '').replace(')', '')}22;color:${color}">DAG</span>
        <div class="detail-title">${d.name}</div>
        <div class="detail-subtitle">${d.scheduleKr}</div>
        <div class="detail-desc">${d.desc}</div>
        <div class="detail-section">
            <div class="detail-section-title">Schedule</div>
            <div class="detail-row"><span class="detail-label">Cron</span><span class="detail-value">${d.schedule}</span></div>
            <div class="detail-row"><span class="detail-label">KST</span><span class="detail-value">${d.scheduleKr}</span></div>
            <div class="detail-row"><span class="detail-label">Catchup</span><span class="detail-value">${d.catchup ? 'Yes' : 'No'}</span></div>
        </div>
        <div class="detail-section">
            <div class="detail-section-title">Reads From (${d.reads.length})</div>
            <ul class="detail-list">${d.reads.map(r => `<li>${r}</li>`).join('')}</ul>
        </div>
        <div class="detail-section">
            <div class="detail-section-title">Writes To (${d.writes.length})</div>
            <ul class="detail-list">${d.writes.map(w => `<li>${w}</li>`).join('')}</ul>
        </div>
        <div class="detail-section">
            <div class="detail-section-title">Tags</div>
            <div style="display:flex;gap:4px;flex-wrap:wrap">
                ${d.tags.map(t => `<span class="dag-tag" style="background:rgba(255,255,255,0.05);color:var(--text-dim)">${t}</span>`).join('')}
            </div>
        </div>
    `;
}

function showTableDetail(t) {
    const color = DOMAIN_COLORS[t.domain] || '#888';
    const writers = EDGES.filter(e => e.target === t.id);
    const readers = EDGES.filter(e => e.source === t.id);

    panel.innerHTML = `
        <span class="detail-badge" style="background:${color}22;color:${color}">${t.domain.toUpperCase()} / ${LAYER_LABELS[t.layer] || t.layer}</span>
        <div class="detail-title" style="font-size:14px">${t.name}</div>
        <div class="detail-subtitle">${t.freq}</div>
        <div class="detail-desc">${t.desc}</div>
        <div class="detail-section">
            <div class="detail-section-title">Schema</div>
            <div class="detail-row"><span class="detail-label">Primary Key</span><span class="detail-value">${t.pk}</span></div>
            <div class="detail-row"><span class="detail-label">Domain</span><span class="detail-value">${t.domain}</span></div>
            <div class="detail-row"><span class="detail-label">Layer</span><span class="detail-value">${LAYER_LABELS[t.layer] || t.layer}</span></div>
            <div class="detail-row"><span class="detail-label">Writer</span><span class="detail-value">${t.writer}</span></div>
        </div>
        ${writers.length ? `<div class="detail-section">
            <div class="detail-section-title">Written By</div>
            <ul class="detail-list">${writers.map(e => `<li>${e.source} <span style="color:var(--text-muted)">${e.label}</span></li>`).join('')}</ul>
        </div>` : ''}
        ${readers.length ? `<div class="detail-section">
            <div class="detail-section-title">Read By</div>
            <ul class="detail-list">${readers.map(e => `<li>${e.target} <span style="color:var(--text-muted)">${e.label}</span></li>`).join('')}</ul>
        </div>` : ''}
    `;
}

function showTopicDetail(t) {
    const producers = EDGES.filter(e => e.target === t.id);
    const consumers = EDGES.filter(e => e.source === t.id);

    panel.innerHTML = `
        <span class="detail-badge" style="background:#FF634722;color:#FF6347">KAFKA TOPIC</span>
        <div class="detail-title">${t.name}</div>
        <div class="detail-subtitle">${t.broker} broker</div>
        <div class="detail-desc">${t.desc}</div>
        <div class="detail-section">
            <div class="detail-section-title">Producers (${producers.length})</div>
            <ul class="detail-list">${producers.map(e => `<li>${e.source}</li>`).join('')}</ul>
        </div>
        <div class="detail-section">
            <div class="detail-section-title">Consumers (${consumers.length})</div>
            <ul class="detail-list">${consumers.map(e => `<li>${e.target}</li>`).join('')}</ul>
        </div>
    `;
}

// === Init ===
initArchGraph();
