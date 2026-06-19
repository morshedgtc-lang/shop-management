const ICONS={
dashboard:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
repairs:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>',
customers:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>',
inventory:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
services:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>',
payments:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>',
expenses:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
daily:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
suppliers:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>',
purchase_orders:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><path d="M9 14l2 2 4-4"/></svg>',
reports:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
staff:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
settings:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>',
shops:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',collections:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',logout:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>'
};
const STATUSES=['PENDING_ESTIMATE','ESTIMATE_GIVEN','APPROVED','WAITING_PARTS','REPAIRED','READY_FOR_PICKUP','COMPLETED'];
const STATUS_COLORS={PENDING_ESTIMATE:'badge-pending',ESTIMATE_GIVEN:'badge-warning',APPROVED:'badge-approved',WAITING_PARTS:'badge-waiting_parts',REPAIRED:'badge-repaired',READY_FOR_PICKUP:'badge-ready',COMPLETED:'badge-delivered'};
const PO_STATUSES=['draft','sent','partially_received','received','cancelled'];
const PO_STATUS_COLORS={draft:'badge-draft',sent:'badge-sent',partially_received:'badge-partial',received:'badge-delivered',cancelled:'badge-cancelled'};
const CURRENCIES=['USD','BDT','INR','NGN'];
const PAYMENT_METHODS=['Cash','bKash','Nagad','Rocket','Card','Bank Transfer','Other'];
let state={page:'dashboard',user:null,settings:{shop_name:'Shop Management',default_currency:'USD'},repairs:{data:[],page:1,total:0},customers:{data:[],page:1,total:0},parts:{data:[],page:1,total:0},services:{data:[],page:1,total:0},payments:{data:[],page:1,total:0},expenses:{data:[],page:1,total:0},daily_sales:{data:[],page:1,total:0},staff:{data:[],page:1,total:0},suppliers:{data:[],page:1,total:0},purchase_orders:{data:[],page:1,total:0},shops:[],collections:{},dashboard:{},reports:{},filters:{},expense_categories:[],catalog:{brands:[],models:[],categories:[],types:[]},current_supplier_id:null,current_po_id:null,settings_tab:'general'};
const $ = id => document.getElementById(id);
async function api(url,opts={}){const token=localStorage.getItem('token');opts.headers={'Content-Type':'application/json',...opts.headers};if(token)opts.headers['Authorization']='Bearer '+token;try{const res=await fetch(url,opts);const data=await res.json();if(res.status===401){localStorage.removeItem('token');state.user=null;render();return{ok:false,status:401,data};}return{ok:res.ok,status:res.status,data};}catch(e){return{ok:false,status:0,data:{error:'Network error'}};}}
function toast(msg,type='info'){const c=document.getElementById('toastContainer');const t=document.createElement('div');t.className='toast '+type;t.textContent=msg;c.appendChild(t);setTimeout(()=>{t.style.opacity='0';t.style.transition='opacity .3s';setTimeout(()=>t.remove(),300);},3000);}
function showModal(html){const o=document.getElementById('modalOverlay');const m=document.getElementById('modalContent');m.innerHTML=html;o.classList.add('active');}
function hideModal(){document.getElementById('modalOverlay').classList.remove('active');}
document.getElementById('modalOverlay').addEventListener('click',e=>{if(e.target===e.currentTarget)hideModal();});
function toggleSidebar(){document.querySelector('.sidebar').classList.toggle('open');document.getElementById('sidebarOverlay').classList.toggle('open');}
function setPage(page){state.page=page;state.filters={};state.current_supplier_id=null;state.current_po_id=null;render();document.querySelector('.sidebar')?.classList.remove('open');document.getElementById('sidebarOverlay')?.classList.remove('open');}
function formatCurrency(amt,cur){return (cur||state.settings.default_currency)+' '+Number(amt||0).toFixed(2);}
function formatDate(d){if(!d)return'-';return new Date(d).toLocaleDateString();}
function formatDateTime(d){if(!d)return'-';return new Date(d).toLocaleString();}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function renderLogin(){return`<div class="login-page"><div class="login-card"><h1>${esc(state.settings.shop_name||'Shop Management')}</h1><p>Admin Panel Login</p><form onsubmit="handleLogin(event)"><div class="form-group"><label>Email</label><input type="email" id="loginEmail" required placeholder="admin@shop.com"></div><div class="form-group"><label>Password</label><input type="password" id="loginPassword" required placeholder="Password"></div><button type="submit" class="btn btn-primary btn-full" id="loginBtn">Sign In</button><div class="error-msg" id="loginError"></div></form></div></div>`;}
async function handleLogin(e){e.preventDefault();const email=document.getElementById('loginEmail').value;const password=document.getElementById('loginPassword').value;const btn=document.getElementById('loginBtn');if(btn){btn.textContent='Signing in...';btn.disabled=true;}const r=await api('/api/auth/login',{method:'POST',body:JSON.stringify({email,password})});if(r.ok){localStorage.setItem('token',r.data.access_token);state.user=r.data.user||{email};toast('Login successful','success');state.page='dashboard';render();loadSettings();loadDashboard();}else{const err=document.getElementById('loginError');if(err)err.textContent=r.data.detail||'Invalid credentials';}if(btn){btn.textContent='Sign In';btn.disabled=false;}}
function renderSidebar(){const navs=[{id:'dashboard',icon:'dashboard',label:'Dashboard'},{id:'repairs',icon:'repairs',label:'Repairs'},{id:'customers',icon:'customers',label:'Customers'},{id:'inventory',icon:'inventory',label:'Inventory'},{id:'services',icon:'services',label:'Services'},{id:'payments',icon:'payments',label:'Payments'},{id:'expenses',icon:'expenses',label:'Expenses'},{id:'daily',icon:'daily',label:'Daily Sales'},{id:'suppliers',icon:'suppliers',label:'Suppliers'},{id:'purchase_orders',icon:'purchase_orders',label:'Purchase Orders'},{id:'reports',icon:'reports',label:'Reports'},{id:'shops',icon:'shops',label:'Shops'},{id:'collections',icon:'collections',label:'Collections'}];const adminNavs=[{id:'staff',icon:'staff',label:'Staff'},{id:'settings',icon:'settings',label:'Settings'}];return`<div class="sidebar" id="sidebar"><div class="sidebar-header"><h2>${esc(state.settings.shop_name||'Shop Management')}</h2><p>Admin Panel</p></div><nav class="sidebar-nav">${navs.map(n=>`<div class="nav-item${state.page===n.id?' active':''}" onclick="setPage('${n.id}')">${ICONS[n.icon]}${n.label}</div>`).join('')}<div class="nav-section">Administration</div>${adminNavs.map(n=>`<div class="nav-item${state.page===n.id?' active':''}" onclick="setPage('${n.id}')">${ICONS[n.icon]}${n.label}</div>`).join('')}</nav><div class="sidebar-footer"><div class="nav-item" onclick="handleLogout()">${ICONS.logout}Logout</div></div></div>`;}
async function handleLogout(){localStorage.removeItem('token');state.user=null;state.page='dashboard';render();toast('Logged out','info');}
async function loadSettings(){const r=await api('/api/settings');if(r.ok){state.settings={...state.settings,...r.data};document.title=state.settings.shop_name||'Shop Management';}}
async function loadDashboard(){const r=await api('/api/dashboard');if(r.ok){state.dashboard=r.data;}render();}
function renderDashboard(){const d=state.dashboard;return`<div class="topbar"><h1>Dashboard</h1><div class="topbar-actions"><button class="btn btn-ghost" onclick="loadDashboard()">Refresh</button></div></div><div class="stats-grid"><div class="stat-card blue"><div class="stat-label">Today's Repairs</div><div class="stat-value">${d.today_repairs||0}</div><div class="stat-sub">Total received today</div></div><div class="stat-card yellow"><div class="stat-label">Pending</div><div class="stat-value">${d.pending||0}</div><div class="stat-sub">Awaiting action</div></div><div class="stat-card purple"><div class="stat-label">In Progress</div><div class="stat-value">${d.in_progress||0}</div><div class="stat-sub">Currently being worked on</div></div><div class="stat-card green"><div class="stat-label">Completed Today</div><div class="stat-value">${d.completed_today||0}</div><div class="stat-sub">Delivered today</div></div><div class="stat-card green"><div class="stat-label">Today's Revenue</div><div class="stat-value">${formatCurrency(d.today_revenue)}</div><div class="stat-sub">Sales + Repair payments</div></div><div class="stat-card red"><div class="stat-label">Today's Expenses</div><div class="stat-value">${formatCurrency(d.today_expenses)}</div><div class="stat-sub">Total spent today</div></div><div class="stat-card cyan"><div class="stat-label">Net Profit</div><div class="stat-value">${formatCurrency(d.net_profit)}</div><div class="stat-sub">Revenue - Expenses</div></div></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:20px"><div class="card"><div class="card-header"><h3>Recent Repairs</h3></div>${(d.recent_repairs||[]).length?`<table><thead><tr><th>ID</th><th>Customer</th><th>Model</th><th>Status</th></tr></thead><tbody>${(d.recent_repairs||[]).map(r=>`<tr><td>#${r.id}</td><td>${esc(r.customer_name||'-')}</td><td>${esc(r.model||'-')}</td><td><span class="badge ${STATUS_COLORS[r.status]||''}">${(r.status||'').replace('_',' ')}</span></td></tr>`).join('')}</tbody></table>`:'<div class="empty">No recent repairs</div>'}</div><div class="card"><div class="card-header"><h3>Low Stock Alerts</h3></div>${(d.low_stock||[]).length?`<table><thead><tr><th>Part</th><th>Model</th><th>Stock</th><th>Min</th></tr></thead><tbody>${(d.low_stock||[]).map(p=>`<tr><td>${esc(p.name)}</td><td>${esc(p.model||'-')}</td><td style="color:var(--danger)">${p.stock_qty}</td><td>${p.min_stock_alert}</td></tr>`).join('')}</tbody></table>`:'<div class="empty">All parts well stocked</div>'}</div></div>`;}
function render(){const app=document.getElementById('app');const token=localStorage.getItem('token');if(!token){app.innerHTML=renderLogin();return;}let pageHtml='';switch(state.page){case'dashboard':pageHtml=renderDashboard();break;case'repairs':pageHtml=renderRepairs();break;case'customers':pageHtml=renderCustomers();break;case'inventory':pageHtml=renderParts();break;case'services':pageHtml=renderServices();break;case'payments':pageHtml=renderPayments();break;case'expenses':pageHtml=renderExpenses();break;case'daily':pageHtml=renderDailySales();break;case'suppliers':pageHtml=renderSuppliers();break;case'purchase_orders':pageHtml=renderPurchaseOrders();break;case'reports':pageHtml=renderReports();break;case'staff':pageHtml=renderStaff();break;case'settings':pageHtml=renderSettings();break;case"shops":pageHtml=renderShops();break;case"collections":pageHtml=renderCollections();break;default:pageHtml=renderDashboard();}app.innerHTML=`<div class="app">${renderSidebar()}<div class="main"><button class="menu-toggle" onclick="toggleSidebar()">&#9776;</button>${pageHtml}</div></div>`;}
async function init(){const token=localStorage.getItem('token');if(token){state.user={};await loadSettings();render();switch(state.page){case'dashboard':loadDashboard();break;case'repairs':loadRepairs();break;case'customers':loadCustomers();break;case'inventory':loadParts();break;case'services':loadServices();break;case'payments':loadPayments();break;case'expenses':loadExpenses();break;case'daily':loadDailySales();break;case'suppliers':loadSuppliers();break;case'purchase_orders':loadPurchaseOrders();break;case'reports':loadReports();break;case'staff':loadStaff();break;case'settings':loadSettingsPage();break;case'shops':loadShops();break;case'collections':loadCollections();break;}}else{render();}}

var ws = null;
var wsReconnectTimer = null;
var wsReconnectDelay = 1000;

function connectWebSocket() {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    var token = localStorage.getItem("token");
    if (!token) return;
    var proto = location.protocol === "https:" ? "wss:" : "ws:";
    var url = proto + "//" + location.host + "/ws?token=" + encodeURIComponent(token);
    try {
        ws = new WebSocket(url);
    } catch(e) { return; }
    ws.onopen = function() { wsReconnectDelay = 1000; };
    ws.onmessage = function(evt) {
        try {
            var msg = JSON.parse(evt.data);
            handleWsEvent(msg);
        } catch(e) {}
    };
    ws.onclose = function() {
        ws = null;
        wsReconnectTimer = setTimeout(function() {
            wsReconnectDelay = Math.min(wsReconnectDelay * 2, 30000);
            connectWebSocket();
        }, wsReconnectDelay);
    };
}

function handleWsEvent(msg) {
    var type = msg.type;
    var data = msg.data || {};
    var toasts = {
        repair_created: "New repair #" + (data.repair_id||"") + " created",
        repair_updated: "Repair #" + (data.repair_id||"") + " updated",
        repair_status_changed: "Repair #" + (data.repair_id||"") + ": " + (data.old_status||"") + " -> " + (data.new_status||""),
        repair_cancelled: "Repair #" + (data.repair_id||"") + " cancelled",
        repair_part_added: "Part added to repair #" + (data.repair_id||""),
        payment_received: "Payment of " + (data.currency||"$") + (data.amount||"0") + " received for repair #" + (data.repair_id||""),
        po_created: "PO " + (data.po_number||"") + " created",
        po_status_changed: "PO " + (data.po_number||"") + ": " + (data.old_status||"") + " -> " + (data.new_status||""),
        po_received: "PO " + (data.po_number||"") + " received",
        stock_updated: "Stock updated: " + (data.name||"") + " (" + (data.sku||"") + ")",
        part_requested: "Part request #" + (data.request_id||"") + " for repair #" + (data.repair_id||""),
        part_fulfilled: "Part request #" + (data.request_id||"") + " fulfilled for repair #" + (data.repair_id||""),
        low_stock_alert: "LOW STOCK: " + (data.name||"") + " (" + (data.sku||"") + ") - only " + (data.stock_qty||"0") + " left",
    };
    if (toasts[type]) toast(toasts[type], type === "low_stock_alert" ? "error" : "info");
    var refreshMap = {
        repair_created: "loadRepairs", repair_updated: "loadRepairs",
        repair_status_changed: "loadRepairs", repair_cancelled: "loadRepairs",
        repair_part_added: "loadRepairs",
        part_requested: "loadRepairs",
        part_fulfilled: "loadRepairs",
        payment_received: "loadPayments",
        po_created: "loadPurchaseOrders", po_status_changed: "loadPurchaseOrders",
        po_received: "loadPurchaseOrders",
        stock_updated: "loadParts", low_stock_alert: "loadParts",
    };
    var fn = refreshMap[type];
    if (fn && typeof window[fn] === "function") window[fn]();
}
