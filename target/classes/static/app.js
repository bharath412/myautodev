let deleteModal;
let selectedEmployees = [];

function showMessage(message, type = 'success') {
    const container = document.getElementById('messageContainer');
    const messageSpan = document.getElementById('alertMessage');
    
    // Set message text
    messageSpan.textContent = message;
    
    // Update alert classes and show
    container.className = `alert alert-${type} alert-dismissible fade show`;
    container.style.display = 'block';
    
    // Force reflow to ensure animation works
    void container.offsetHeight;
    
    // Auto hide after 5 seconds
    setTimeout(() => {
        container.classList.remove('show');
        setTimeout(() => {
            container.style.display = 'none';
        }, 150); // Match Bootstrap fade duration
    }, 5000);
}

document.addEventListener('DOMContentLoaded', function() {
    loadEmployees();

    // Initialize Bootstrap modal
    deleteModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    
    // Initialize delete button handler
    document.getElementById('deleteSelectedBtn').addEventListener('click', function(e) {
        e.preventDefault();
        const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
        const count = checkboxes.length;
        
        if (count > 0) {
            document.getElementById('deleteConfirmMessage').textContent = 
                `Are you sure you want to delete ${count} employee(s)?`;
            deleteModal.show();
        }
    });

    // Handle confirm delete button
    document.getElementById('confirmDeleteBtn').addEventListener('click', async function() {
        const selectedIds = Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
            .map(cb => cb.value);
            
        try {
            const response = await fetch('/api/employees/batch', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(selectedIds)
            });

            if (response.ok) {
                showMessage('Successfully deleted ' + selectedIds.length + ' employee(s)', 'success');
                loadEmployees(); // Refresh the list
            } else {
                showMessage('Error deleting employees', 'danger');
            }
        } catch (error) {
            showMessage('Error: ' + error.message, 'danger');
        }
        
        deleteModal.hide();
    });

    // Form submission
    document.getElementById('employeeForm').addEventListener('submit', function(e) {
        e.preventDefault();
        saveEmployee();
    });

    // Navigation handling
    document.getElementById('addEmployeeNav').addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelector('.nav-link.active').classList.remove('active');
        this.classList.add('active');
        document.getElementById('formTitle').textContent = 'Add Employee';
        document.getElementById('saveBtn').textContent = 'Save';
        resetForm();
    });

    document.getElementById('employeeListNav').addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelector('.nav-link.active').classList.remove('active');
        this.classList.add('active');
        loadEmployees();
    });
});

function loadEmployees() {
    fetch('/api/employees')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load employees');
            }
            return response.json();
        })
        .then(data => {
            const table = document.getElementById('employeeTable');
            table.innerHTML = '';

            if (data.length > 0) {
                const headerRow = table.insertRow();
                headerRow.innerHTML = `
                    <th><input type="checkbox" id="selectAll"></th>
                    <th>First Name</th>
                    <th>Last Name</th>
                    <th>Email</th>
                    <th>Department</th>
                    <th>Actions</th>
                `;

                // Add select all functionality
                document.getElementById('selectAll').addEventListener('change', function() {
                    const checkboxes = document.querySelectorAll('.employee-checkbox');
                    checkboxes.forEach(checkbox => checkbox.checked = this.checked);
                    updateDeleteSelectedButton();
                });
            }

            data.forEach(employee => {
                const row = table.insertRow();
                row.dataset.employeeId = employee.id;
                row.innerHTML = `
                    <td>
                        <input type="checkbox" class="employee-checkbox" value="${employee.id}">
                    </td>
                    <td>${employee.firstName}</td>
                    <td>${employee.lastName}</td>
                    <td>${employee.email}</td>
                    <td>${employee.department}</td>
                    <td>
                        <button class="btn btn-sm btn-warning" onclick="editEmployee(${employee.id})">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteEmployee(${employee.id})">Delete</button>
                    </td>
                `;
            });

            // Add checkbox event listeners
            document.querySelectorAll('.employee-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', updateDeleteSelectedButton);
            });

            updateDeleteSelectedButton();
        })
        .catch(error => {
            console.error('Error loading employees:', error);
            showMessage('Error loading employees. Please try again.', 'danger');
        });
}

function updateDeleteSelectedButton() {
    const selectedCount = document.querySelectorAll('.employee-checkbox:checked').length;
    let deleteSelectedBtn = document.getElementById('deleteSelectedBtn');
    
    if (!deleteSelectedBtn) {
        const container = document.querySelector('.card-header');
        if (container) {
            deleteSelectedBtn = document.createElement('button');
            deleteSelectedBtn.id = 'deleteSelectedBtn';
            deleteSelectedBtn.className = 'btn btn-danger float-end';
            deleteSelectedBtn.onclick = deleteSelectedEmployees;
            container.appendChild(deleteSelectedBtn);
        } else {
            return; // Exit if container not found
        }
    }
    
    deleteSelectedBtn.textContent = `Delete Selected (${selectedCount})`;
    deleteSelectedBtn.style.display = selectedCount > 0 ? 'block' : 'none';
}

function deleteSelectedEmployees() {
    const selectedIds = Array.from(document.querySelectorAll('.employee-checkbox:checked'))
        .map(checkbox => checkbox.value);

    if (selectedIds.length === 0) return;

    if (confirm(`Are you sure you want to delete ${selectedIds.length} employee(s)?`)) {
        // Clear table immediately to prevent stale data
        const table = document.getElementById('employeeTable');
        table.innerHTML = '';

        Promise.all(selectedIds.map(id =>
            fetch(`/api/employees/${id}`, { method: 'DELETE' })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Failed to delete employee ${id}`);
                    }
                })
        ))
        .then(() => {
            showMessage(`Successfully deleted ${selectedIds.length} employee(s)`, 'success');
            // Wait for backend to process deletions
            setTimeout(() => {
                fetch('/api/employees')
                    .then(response => response.json())
                    .then(() => loadEmployees())
                    .catch(error => {
                        console.error('Error refreshing employees:', error);
                        loadEmployees(); // Try loading anyway
                    });
            }, 1000);
        })
        .catch(error => {
            console.error('Error during deletion:', error);
            showMessage('Error deleting employees. Please try again.', 'danger');
            loadEmployees(); // Refresh to show current state
        });
    }
}

function saveEmployee() {
    const employeeData = {
        firstName: document.getElementById('firstName').value,
        lastName: document.getElementById('lastName').value,
        email: document.getElementById('email').value,
        department: document.getElementById('department').value
    };

    const id = document.getElementById('employeeId').value;
    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/employees/${id}` : '/api/employees';

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(employeeData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to save employee');
        }
        return response.json();
    })
    .then(data => {
        // Show success message
        const messageText = id ? 'Employee updated successfully' : 'Employee created successfully';
        showMessage(messageText, 'success');
        resetForm();
        loadEmployees();
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Error saving employee: ' + error.message, 'danger');
    });
}

function editEmployee(id) {
    fetch(`/api/employees/${id}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch employee');
            }
            return response.json();
        })
        .then(employee => {
            document.getElementById('employeeId').value = employee.id;
            document.getElementById('firstName').value = employee.firstName;
            document.getElementById('lastName').value = employee.lastName;
            document.getElementById('email').value = employee.email;
            document.getElementById('department').value = employee.department;
            document.getElementById('formTitle').innerText = 'Edit Employee';
            document.getElementById('saveBtn').innerText = 'Update';
        })
        .catch(error => {
            console.error('Error fetching employee:', error);
            showMessage('Error loading employee details. Please try again.', 'danger');
        });
}

function deleteEmployee(id) {
    if (confirm('Are you sure you want to delete this employee?')) {
        fetch(`/api/employees/${id}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to delete employee');
            }
            showMessage('Employee deleted successfully', 'success');
            loadEmployees();
        })
        .catch(error => {
            console.error('Error deleting employee:', error);
            showMessage('Error deleting employee. Please try again.', 'danger');
        });
    }
}

function resetForm() {
    document.getElementById('employeeForm').reset();
    document.getElementById('employeeId').value = '';
    document.getElementById('formTitle').innerText = 'Add Employee';

}    document.getElementById('saveBtn').innerText = 'Save';

