package com.example.employeemanagement.model;

import lombok.Data;

@Data
public class Employee {
    private Long id;
    private String firstName;
    private String lastName;
    private String email;
    private String department;
}
