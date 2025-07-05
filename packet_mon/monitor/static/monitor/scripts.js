// Sample device data (in production, this would come from an API)
const devices = [
    {
        id: 1,
        name: "Router-1",
        ip: "192.168.1.1",
        status: "online",
        cpu: 35,
        memory: 45,
        bandwidth: "100/50 Mbps",
        latency: "12ms",
        uptime: "15d 6h"
    },
    {
        id: 2,
        name: "Server-1",
        ip: "192.168.1.10",
        status: "warning",
        cpu: 85,
        memory: 75,
        bandwidth: "500/200 Mbps",
        latency: "5ms",
        uptime: "7d 2h"
    },
    {
        id: 3,
        name: "Switch-1",
        ip: "192.168.1.2",
        status: "offline",
        cpu: 0,
        memory: 0,
        bandwidth: "0/0 Mbps",
        latency: "N/A",
        uptime: "0d 0h"
    }
];

// DOM Elements
const deviceList = document.getElementById('deviceList');
const deviceSearch = document.getElementById('deviceSearch');
const statusFilter = document.getElementById('statusFilter');
const sortBy = document.getElementById('sortBy');

// Initialize dashboard
function initDashboard() {
    renderDeviceTable(devices);
    initCharts();
    setupEventListeners();
    startLiveUpdates();
}

// Render device table
function renderDeviceTable(devices) {
    deviceList.innerHTML = devices.map(device => `
        <tr>
            <td>${device.name}</td>
            <td>${device.ip}</td>
            <td>
                <span class="badge ${getStatusClass(device.status)}">
                    ${device.status.toUpperCase()}
                </span>
            </td>
            <td>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar ${getCpuClass(device.cpu)}" 
                         role="progressbar" 
                         style="width: ${device.cpu}%" 
                         aria-valuenow="${device.cpu}" 
                         aria-valuemin="0" 
                         aria-valuemax="100">
                        ${device.cpu}%
                    </div>
                </div>
            </td>
            <td>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar ${getMemoryClass(device.memory)}" 
                         role="progressbar" 
                         style="width: ${device.memory}%" 
                         aria-valuenow="${device.memory}" 
                         aria-valuemin="0" 
                         aria-valuemax="100">
                        ${device.memory}%
                    </div>
                </div>
            </td>
            <td>${device.bandwidth}</td>
            <td>${device.latency}</td>
            <td>${device.uptime}</td>
            
            <td>
    <button class="btn btn-sm btn-outline-primary me-1" onclick="editDevice(${device.id})">
        <i class="bi bi-pencil"></i> Edit
    </button>
    <button class="btn btn-sm btn-outline-danger" onclick="removeDevice(${device.id})">
        <i class="bi bi-trash"></i> Remove
    </button>
</td>
        </tr>
    `).join('');
}

// Add these new functions at the end of the file:
function editDevice(deviceId) {
    // Store the device ID in localStorage to access it in edit.html
    localStorage.setItem('editDeviceId', deviceId);
    // Redirect to edit page
    window.location.href = 'edit.html';
}

function removeDevice(deviceId) {
    if (confirm('Are you sure you want to remove this device?')) {
        // In a real app, this would be an API call to delete the device
        const index = devices.findIndex(d => d.id === deviceId);
        if (index !== -1) {
            devices.splice(index, 1);
            renderDeviceTable(devices);
            alert('Device removed successfully!');
        }
    }
}



// Get status badge class
function getStatusClass(status) {
    return {
        online: 'bg-success',
        warning: 'bg-warning text-dark',
        offline: 'bg-danger'
    }[status];
}

// Get CPU progress bar class
function getCpuClass(cpu) {
    if (cpu > 80) return 'bg-danger';
    if (cpu > 60) return 'bg-warning';
    return 'bg-success';
}

// Get Memory progress bar class
function getMemoryClass(memory) {
    if (memory > 80) return 'bg-danger';
    if (memory > 60) return 'bg-warning';
    return 'bg-success';
}

// Initialize charts
function initCharts() {
    // CPU Chart
    new Chart(document.getElementById('cpuChart'), {
        type: 'line',
        data: {
            labels: Array(24).fill().map((_, i) => `${i}:00`),
            datasets: [{
                label: 'CPU Usage %',
                data: Array(24).fill().map(() => Math.floor(Math.random() * 100)),
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                tension: 0.4,
                fill: true
            }]
        }
    });

    // Memory Chart
    new Chart(document.getElementById('memoryChart'), {
        type: 'line',
        data: {
            labels: Array(24).fill().map((_, i) => `${i}:00`),
            datasets: [{
                label: 'Memory Usage %',
                data: Array(24).fill().map(() => Math.floor(Math.random() * 100)),
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                tension: 0.4,
                fill: true
            }]
        }
    });
}

// Set up event listeners
function setupEventListeners() {
    deviceSearch.addEventListener('input', filterDevices);
    statusFilter.addEventListener('change', filterDevices);
    sortBy.addEventListener('change', sortDevices);
}

// Filter devices
function filterDevices() {
    const searchTerm = deviceSearch.value.toLowerCase();
    const statusFilterValue = statusFilter.value;

    const filtered = devices.filter(device => {
        const matchesSearch = device.name.toLowerCase().includes(searchTerm) ||
            device.ip.includes(searchTerm);
        const matchesStatus = !statusFilterValue || device.status === statusFilterValue;
        return matchesSearch && matchesStatus;
    });

    renderDeviceTable(filtered);
}

// Sort devices
function sortDevices() {
    const sortByValue = sortBy.value;
    const sorted = [...devices];

    sorted.sort((a, b) => {
        if (sortByValue === 'name') return a.name.localeCompare(b.name);
        if (sortByValue === 'cpu') return b.cpu - a.cpu;
        if (sortByValue === 'memory') return b.memory - a.memory;
        if (sortByValue === 'latency') {
            const aLatency = a.latency === 'N/A' ? Infinity : parseInt(a.latency);
            const bLatency = b.latency === 'N/A' ? Infinity : parseInt(b.latency);
            return aLatency - bLatency;
        }
        return 0;
    });

    renderDeviceTable(sorted);
}

// Simulate live updates
function startLiveUpdates() {
    setInterval(() => {
        // In a real app, this would be an API call
        devices.forEach(device => {
            if (device.status !== 'offline') {
                device.cpu = Math.min(100, Math.max(0, device.cpu + (Math.random() * 10 - 5)));
                device.memory = Math.min(100, Math.max(0, device.memory + (Math.random() * 5 - 2.5)));
                device.latency = `${Math.max(1, Math.floor(parseInt(device.latency) + (Math.random() * 10 - 5)))}ms`;
            }
        });
        renderDeviceTable(devices);
    }, 5000);
}

// Initialize the dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', initDashboard);

function showDeviceDetails(deviceId) {
    const device = devices.find(d => d.id === deviceId);
    if (device) {
        alert(`
Device Name: ${device.name}
IP Address: ${device.ip}
Status: ${device.status.toUpperCase()}
CPU Usage: ${device.cpu}%
Memory Usage: ${device.memory}%
Bandwidth: ${device.bandwidth}
Latency: ${device.latency}
Uptime: ${device.uptime}
        `);
    }
}
