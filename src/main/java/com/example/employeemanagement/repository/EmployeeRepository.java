package com.example.employeemanagement.repository;

import com.example.employeemanagement.model.Employee;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Repository;

@Repository
public class EmployeeRepository {
    private final ConcurrentHashMap<Long, Employee> employees = new ConcurrentHashMap<>();
    private final AtomicLong idGenerator = new AtomicLong(0L);

    public List<Employee> findAll() {
        return new ArrayList<>(employees.values());
    }

    public Optional<Employee> findById(Long id) {
        return Optional.ofNullable(employees.get(id));
    }

    public Employee save(Employee employee) {
        if (employee.getId() == null) {
            employee.setId(idGenerator.incrementAndGet());
        }
        employees.put(employee.getId(), employee);
        return employee;
    }

    public void deleteById(Long id) {
        employees.remove(id);
    }
}
