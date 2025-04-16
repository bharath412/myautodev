*** Settings ***
Library    RequestsLibrary
Library    SeleniumLibrary
Library    Collections
Library    FakerLibrary

Suite Setup       Setup Test Suite
Suite Teardown    Close All Browsers

*** Variables ***
${BASE_URL}         http://localhost:8081
${FRONTEND_URL}     http://localhost:8081
${BROWSER}          edge

# API Endpoints
${EMPLOYEES_ENDPOINT}    ${BASE_URL}/api/employees

# Web Elements
${FIRST_NAME_INPUT}     id:firstName
${LAST_NAME_INPUT}      id:lastName
${EMAIL_INPUT}          id:email
${DEPARTMENT_INPUT}     id:department
${SAVE_BTN}            id:saveBtn
${EMPLOYEE_TABLE}      id:employeeTable
${TABLE_ROWS}         css:#employeeTable tr
${MESSAGE_CONTAINER}   id:messageContainer
${DELETE_SELECTED_BTN}  id:deleteSelectedBtn
${ADD_EMPLOYEE_NAV}    id:addEmployeeNav
${EMPLOYEE_LIST_NAV}   id:employeeListNav
${NAVBAR_BRAND}        css:.navbar-brand

*** Keywords ***
Setup Test Suite
    Set Selenium Timeout    10 seconds
    Set Selenium Speed    0.1 seconds
    Create Session    employee_api    ${BASE_URL}    verify=True
    Open Browser    ${FRONTEND_URL}    ${BROWSER}
    Maximize Browser Window
    Set Window Size    1920    1080
    Sleep    1s    # Give the browser time to fully initialize

Generate Random Employee Data
    ${first_name}=    FakerLibrary.First Name
    ${last_name}=     FakerLibrary.Last Name
    ${email}=         FakerLibrary.Email
    ${department}=    FakerLibrary.Job
    &{employee}=     Create Dictionary    
    ...    firstName=${first_name}    
    ...    lastName=${last_name}    
    ...    email=${email}
    ...    department=${department}
    RETURN    &{employee}

Create Employee Via API
    [Arguments]    ${employee_data}
    ${response}=    POST On Session    
    ...    employee_api    
    ...    /api/employees    
    ...    json=${employee_data}
    Status Should Be    201    ${response}
    RETURN    ${response.json()}

Select Multiple Employees
    [Arguments]    @{employee_names}
    Execute JavaScript    window.scrollTo(0, 0)
    Sleep    1s
    FOR    ${name}    IN    @{employee_names}
        ${checkbox}=    Set Variable    xpath://tr[contains(., '${name}')]//input[@type='checkbox']
        Wait Until Element Is Visible    ${checkbox}
        ${checkbox_id}=    Get Element Attribute    ${checkbox}    id
        Execute JavaScript    document.evaluate("//tr[contains(., '${name}')]//input[@type='checkbox']", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click()
        Sleep    1s
    END
    Wait Until Element Is Visible    ${DELETE_SELECTED_BTN}

Delete Selected Employees
    Click Element    ${DELETE_SELECTED_BTN}
    Handle Alert    ACCEPT
    Sleep    1s    # Wait for deletion operations to complete
    Wait Until Element Is Visible    ${MESSAGE_CONTAINER}
    ${message}=    Get Text    ${MESSAGE_CONTAINER}
    Should Match Regexp    ${message}    ^Successfully deleted \d+ employee\(s\)$
    Wait Until Element Is Visible    ${EMPLOYEE_TABLE}

*** Test Cases ***
Verify Navigation
    Go To    ${FRONTEND_URL}
    Wait Until Element Is Visible    ${NAVBAR_BRAND}
    Element Text Should Be    ${NAVBAR_BRAND}    Employee Management
    Element Should Be Visible    ${ADD_EMPLOYEE_NAV}
    Element Should Be Visible    ${EMPLOYEE_LIST_NAV}
    Element Text Should Be    ${ADD_EMPLOYEE_NAV}    Add Employee
    Element Text Should Be    ${EMPLOYEE_LIST_NAV}    Employee List

Create And Delete Two Employees
    # Switch to Add Employee view and reset scroll
    Go To    ${FRONTEND_URL}
    Execute JavaScript    window.scrollTo(0, 0)
    Sleep    1s
    Wait Until Element Is Visible    ${ADD_EMPLOYEE_NAV}
    Wait Until Element Is Enabled    ${ADD_EMPLOYEE_NAV}
    Click Element    ${ADD_EMPLOYEE_NAV}
    
    # Create first employee via UI
    Wait Until Element Is Visible    ${FIRST_NAME_INPUT}
    ${employee_data1}=    Generate Random Employee Data
    Input Text    ${FIRST_NAME_INPUT}    ${employee_data1}[firstName]
    Input Text    ${LAST_NAME_INPUT}     ${employee_data1}[lastName]
    Input Text    ${EMAIL_INPUT}         ${employee_data1}[email]
    Input Text    ${DEPARTMENT_INPUT}    ${employee_data1}[department]
    Wait Until Element Is Enabled    ${SAVE_BTN}
    Execute JavaScript    document.getElementById('saveBtn').click()
    Wait Until Element Contains    ${MESSAGE_CONTAINER}    Employee created successfully
    Sleep    1s
    
    # Create second employee
    Execute JavaScript    window.scrollTo(0, 0)
    Sleep    1s
    Wait Until Element Is Visible    ${ADD_EMPLOYEE_NAV}
    Wait Until Element Is Enabled    ${ADD_EMPLOYEE_NAV}
    Click Element    ${ADD_EMPLOYEE_NAV}
    Wait Until Element Is Visible    ${FIRST_NAME_INPUT}
    ${employee_data2}=    Generate Random Employee Data
    Input Text    ${FIRST_NAME_INPUT}    ${employee_data2}[firstName]
    Input Text    ${LAST_NAME_INPUT}     ${employee_data2}[lastName]
    Input Text    ${EMAIL_INPUT}         ${employee_data2}[email]
    Input Text    ${DEPARTMENT_INPUT}    ${employee_data2}[department]
    Wait Until Element Is Enabled    ${SAVE_BTN}
    Execute JavaScript    document.getElementById('saveBtn').click()
    Wait Until Element Contains    ${MESSAGE_CONTAINER}    Employee created successfully
    Sleep    1s
    
    # Switch to Employee List view
    Execute JavaScript    window.scrollTo(0, 0)
    Sleep    1s
    Wait Until Element Is Visible    ${EMPLOYEE_LIST_NAV}
    Wait Until Element Is Enabled    ${EMPLOYEE_LIST_NAV}
    Click Element    ${EMPLOYEE_LIST_NAV}
    Wait Until Element Is Visible    ${EMPLOYEE_TABLE}
    Sleep    2s
    
    # Select and delete both employees
    Select Multiple Employees    ${employee_data1}[firstName]    ${employee_data2}[firstName]
    Wait Until Element Is Enabled    ${DELETE_SELECTED_BTN}
    Execute JavaScript    document.getElementById('deleteSelectedBtn').click()
    Handle Alert    ACCEPT
    Sleep    2s
    
    # Verify deletion message and table refresh
    Wait Until Element Contains    ${MESSAGE_CONTAINER}    Successfully deleted 2 employee(s)
    Sleep    2s    # Wait for table refresh
    
    # Verify employees are gone from UI
    ${table}=    Get Text    ${EMPLOYEE_TABLE}
    Should Not Contain    ${table}    ${employee_data1}[firstName]
    Should Not Contain    ${table}    ${employee_data2}[firstName]
    
    # Double check with API
    ${response}=    GET On Session    employee_api    /api/employees
    ${employees}=    Set Variable    ${response.json()}
    FOR    ${employee}    IN    @{employees}
        Should Not Be Equal    ${employee}[firstName]    ${employee_data1}[firstName]
        Should Not Be Equal    ${employee}[firstName]    ${employee_data2}[firstName]
    END
