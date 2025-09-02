// Cat TV Control Panel JavaScript

// Initialize Socket.IO
const socket = io();

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('Connected to server');
    loadHistory();
    loadSchedules();
});

socket.on('status_update', (data) => {
    updateStatus(data);
});

// Modal functions
function showAddScheduleModal() {
    document.getElementById('schedule-modal').classList.add('show');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

// Status functions
function updateStatus(data) {
    // Update player status
    if (data.player) {
        const playerEl = document.getElementById('player-status');
        playerEl.querySelector('.value').textContent = data.player.is_playing ? 'PLAYING' : 'STOPPED';
        playerEl.className = `status-item ${data.player.is_playing ? 'active' : 'inactive'}`;
        
        const videoEl = document.getElementById('current-video');
        const title = data.player.current_video ? data.player.current_video.title : 'None';
        videoEl.querySelector('.value').textContent = title.length > 50 ? title.substring(0, 50) + '...' : title;
    }
    
    // Update display status
    if (data.display) {
        const displayEl = document.getElementById('display-status');
        const toggleButton = document.getElementById('display-toggle');
        
        if (data.display.available) {
            const isOn = !data.display.is_blank;
            displayEl.querySelector('.value').textContent = isOn ? 'ON' : 'OFF';
            displayEl.className = `status-item ${isOn ? 'active' : 'inactive'}`;
            
            // Update toggle button text and style
            if (toggleButton) {
                toggleButton.textContent = isOn ? 'Turn Display Off' : 'Turn Display On';
                toggleButton.className = isOn ? 'btn-danger' : 'btn-success';
            }
        } else {
            displayEl.querySelector('.value').textContent = 'N/A';
            displayEl.className = 'status-item';
            
            if (toggleButton) {
                toggleButton.textContent = 'Display N/A';
                toggleButton.disabled = true;
            }
        }
    }
    
    // Update time
    if (data.time) {
        const time = new Date(data.time);
        document.getElementById('system-time').querySelector('.value').textContent = 
            time.toLocaleTimeString();
    }
}

// Display control
async function toggleDisplay() {
    try {
        // Get current display status
        const statusResponse = await fetch('/api/display/status');
        const statusData = await statusResponse.json();
        
        if (!statusData.available) {
            alert('Display control not available');
            return;
        }
        
        // Determine action based on current state
        const isCurrentlyOn = !statusData.is_blank;
        const action = isCurrentlyOn ? 'off' : 'on';
        
        // Disable button during operation
        const toggleButton = document.getElementById('display-toggle');
        if (toggleButton) {
            toggleButton.disabled = true;
            toggleButton.textContent = 'Working...';
        }
        
        const response = await fetch(`/api/display/${action}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log(`Display ${action}: ${result.message}`);
        } else {
            alert(`Error: ${result.error || 'Unknown error'}`);
        }
        
    } catch (error) {
        console.error('Display control error:', error);
        alert('Failed to control display: ' + error.message);
    } finally {
        // Re-enable button
        const toggleButton = document.getElementById('display-toggle');
        if (toggleButton) {
            toggleButton.disabled = false;
        }
    }
}

// Schedule management
async function loadSchedules() {
    try {
        const response = await fetch('/api/schedules');
        const schedules = await response.json();
        
        const tbody = document.querySelector('#schedules-table tbody');
        tbody.innerHTML = '';
        
        // Get current time to show if schedule is active
        const now = new Date();
        const currentTime = now.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', hour12: true}); // 12-hour format
        const currentDay = now.getDay(); // 0 = Sunday, 1 = Monday, etc
        // Convert to our format (0 = Monday)
        const dayOfWeek = currentDay === 0 ? 6 : currentDay - 1;
        
        // Helper function to convert time to minutes for comparison
        const timeToMinutes = (timeStr) => {
            const [time, period] = timeStr.split(' ');
            let [hours, minutes] = time.split(':').map(Number);
            if (period === 'PM' && hours !== 12) hours += 12;
            if (period === 'AM' && hours === 12) hours = 0;
            return hours * 60 + minutes;
        };
        
        const currentMinutes = timeToMinutes(currentTime);
        
        schedules.forEach(schedule => {
            const days = schedule.days_of_week.split(',').map(d => 
                ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][parseInt(d)]
            ).join(', ');
            
            // Check if currently active
            const startMinutes = timeToMinutes(schedule.start_time);
            const endMinutes = timeToMinutes(schedule.end_time);
            
            let isInTimeWindow;
            if (startMinutes <= endMinutes) {
                // Normal schedule (e.g., 2:00 PM - 5:00 PM)
                isInTimeWindow = currentMinutes >= startMinutes && currentMinutes <= endMinutes;
            } else {
                // Schedule crosses midnight (e.g., 11:00 PM - 2:00 AM)
                isInTimeWindow = currentMinutes >= startMinutes || currentMinutes <= endMinutes;
            }
            
            const isCurrentlyActive = schedule.is_active && 
                schedule.days_of_week.split(',').includes(dayOfWeek.toString()) &&
                isInTimeWindow;
            
            const statusText = isCurrentlyActive ? '🟢 ACTIVE NOW' : 
                             schedule.is_active ? '⭕ Scheduled' : '❌ Disabled';
            
            const row = tbody.insertRow();
            row.setAttribute('data-schedule-id', schedule.id);
            row.innerHTML = `
                <td><strong>${schedule.name}</strong></td>
                <td>${schedule.start_time}</td>
                <td>${schedule.end_time}</td>
                <td>${days}</td>
                <td>${statusText}</td>
                <td>
                    <button onclick="editSchedule(${schedule.id})" style="margin-right: 5px;">Edit</button>
                    <button onclick="deleteSchedule(${schedule.id})" class="btn-danger">Delete</button>
                </td>
            `;
            
            // Highlight active schedule
            if (isCurrentlyActive) {
                row.style.backgroundColor = '#d4f4dd';
            }
        });
    } catch (error) {
        console.error('Error loading schedules:', error);
    }
}

async function saveSchedule(event) {
    event.preventDefault();
    
    console.log('Saving schedule...');
    
    const days = [];
    for (let i = 0; i < 7; i++) {
        if (document.getElementById(`day-${i}`).checked) {
            days.push(i);
        }
    }
    
    const data = {
        name: document.getElementById('schedule-name').value,
        start_time: document.getElementById('schedule-start').value,
        end_time: document.getElementById('schedule-end').value,
        days_of_week: days.join(','),
        is_active: true
    };
    
    console.log('Schedule data:', data);
    
    // Basic validation
    if (!data.name || !data.start_time || !data.end_time) {
        alert('Please fill in all required fields');
        return;
    }
    
    if (days.length === 0) {
        alert('Please select at least one day');
        return;
    }
    
    // Check if we're updating or creating
    const scheduleId = document.getElementById('schedule-form').dataset.scheduleId;
    const isUpdate = scheduleId && scheduleId !== '';
    
    try {
        console.log('Sending request...');
        const url = isUpdate ? `/api/schedules/${scheduleId}` : '/api/schedules';
        const method = isUpdate ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        console.log('Response status:', response.status);
        const result = await response.json();
        console.log('Response data:', result);
        
        if (response.ok) {
            alert(isUpdate ? 'Schedule updated successfully!' : 'Schedule saved successfully!');
            closeModal('schedule-modal');
            loadSchedules();
            document.getElementById('schedule-form').reset();
            delete document.getElementById('schedule-form').dataset.scheduleId;
            
            // Reset modal for next use
            document.querySelector('.modal-header h3').textContent = 'Add Schedule';
            document.querySelector('#schedule-form button[type="submit"]').textContent = 'Save Schedule';
            
            // Check all days by default for next time
            for (let i = 0; i < 7; i++) {
                document.getElementById(`day-${i}`).checked = true;
            }
        } else {
            alert('Error saving schedule: ' + (result.message || result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Save error:', error);
        alert('Error saving schedule: ' + error.message);
    }
}

async function editSchedule(id) {
    try {
        // Find the schedule in our loaded data
        const scheduleRow = document.querySelector(`tr[data-schedule-id="${id}"]`);
        if (!scheduleRow) {
            alert('Schedule not found');
            return;
        }
        
        // Get schedule data from the row
        const cells = scheduleRow.querySelectorAll('td');
        const name = cells[0].textContent;
        const startTime = cells[1].textContent;
        const endTime = cells[2].textContent;
        const daysText = cells[3].textContent;
        
        // Convert 12-hour to 24-hour for input fields
        const convertTo24Hour = (time12) => {
            const [time, period] = time12.split(' ');
            let [hours, minutes] = time.split(':');
            hours = parseInt(hours);
            
            if (period === 'PM' && hours !== 12) {
                hours += 12;
            } else if (period === 'AM' && hours === 12) {
                hours = 0;
            }
            
            return `${hours.toString().padStart(2, '0')}:${minutes}`;
        };
        
        // Set form values
        document.getElementById('schedule-name').value = name;
        document.getElementById('schedule-start').value = convertTo24Hour(startTime);
        document.getElementById('schedule-end').value = convertTo24Hour(endTime);
        
        // Parse days of week
        const dayMap = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6};
        const activeDays = daysText.split(', ').map(day => dayMap[day]).filter(d => d !== undefined);
        
        // Set checkboxes
        for (let i = 0; i < 7; i++) {
            document.getElementById(`day-${i}`).checked = activeDays.includes(i);
        }
        
        // Store the ID for update
        document.getElementById('schedule-form').dataset.scheduleId = id;
        
        // Update modal title and button
        document.querySelector('.modal-header h3').textContent = 'Edit Schedule';
        document.querySelector('#schedule-form button[type="submit"]').textContent = 'Update Schedule';
        
        // Show modal
        showAddScheduleModal();
        
    } catch (error) {
        console.error('Error editing schedule:', error);
        alert('Error loading schedule for editing');
    }
}

async function deleteSchedule(id) {
    if (confirm('Delete this schedule?')) {
        try {
            const response = await fetch(`/api/schedules/${id}`, {method: 'DELETE'});
            const result = await response.json();
            if (response.ok) {
                loadSchedules();
            } else {
                alert('Error deleting schedule: ' + result.message);
            }
        } catch (error) {
            alert('Error deleting schedule: ' + error);
        }
    }
}

// History
async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        const history = await response.json();
        
        const tbody = document.querySelector('#history-table tbody');
        tbody.innerHTML = '';
        
        history.forEach(entry => {
            const row = tbody.insertRow();
            const startTime = entry.started_at ? 
                new Date(entry.started_at).toLocaleString() : '-';
            const title = entry.video_title || 'Unknown';
            
            row.innerHTML = `
                <td title="${title}">${title.length > 60 ? title.substring(0, 60) + '...' : title}</td>
                <td>${startTime}</td>
                <td>${entry.status}</td>
            `;
        });
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

// Auto-refresh
setInterval(loadHistory, 30000);   // Refresh history every 30 seconds