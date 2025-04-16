*** Settings ***
Library    RequestsLibrary
Library    SeleniumLibrary
Library    Collections
Library    FakerLibrary
Library    OperatingSystem

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
${DELETE_CONFIRM_BTN}   id:confirmDeleteBtn
${DELETE_MODAL}         id:deleteConfirmModal
${DELETE_MESSAGE}       id:deleteConfirmMessage

*** Keywords ***
Setup Test Suite
    Set Selenium Timeout    30 seconds    # Increased timeout
    Set Selenium Speed      0.2 seconds   # Faster execution but still stable
    Set Selenium Implicit Wait    5 seconds
    Create Session    employee_api    ${BASE_URL}    verify=True    disable_warnings=1
    Open Browser    ${FRONTEND_URL}    ${BROWSER}
    Maximize Browser Window
    Set Window Size    1920    1080
    Sleep    1s
    Log    Starting test suite on ${BASE_URL}
    ${response}    GET On Session    employee_api    /api/employees    expected_status=any
    Log    API Response Status: ${response.status_code}
    Run Keyword If    '${response.status_code}' != '200'    Fatal Error    API not responding correctly

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
    [Arguments]    ${expected_count}
    # Click delete button and wait for modal
    Wait Until Element Is Enabled    ${DELETE_SELECTED_BTN}    timeout=30s
    Click Element    ${DELETE_SELECTED_BTN}
    
    # Wait for modal and verify message
    Wait Until Element Is Visible    ${DELETE_MODAL}    timeout=30s
    Wait Until Element Contains    ${DELETE_MESSAGE}    Are you sure you want to delete ${expected_count} employee(s)?    timeout=30s
    
    # Confirm deletion
    Wait Until Element Is Enabled    ${DELETE_CONFIRM_BTN}    timeout=30s
    Click Element    ${DELETE_CONFIRM_BTN}
    
    # Wait for modal to close
    Wait Until Element Is Not Visible    ${DELETE_MODAL}    timeout=30s
    Sleep    1s

    # Verify deletion via API
    ${response}=    GET On Session    employee_api    /api/employees
    ${employees}=    Set Variable    ${response.json()}
    Length Should Be    ${employees}    0

Capture Error State
    [Arguments]    ${error_message}
    Capture Page Screenshot
    Log    Error occurred: ${error_message}
    ${page_source}=    Get Source
    Create File    error_page.html    ${page_source}
    Log    Page source saved to error_page.html

Wait For Success Message
    [Arguments]    ${expected_message}
    Wait Until Element Is Visible    ${MESSAGE_CONTAINER}    timeout=30s
    Wait Until Element Contains    ${MESSAGE_CONTAINER}    ${expected_message}    timeout=30s
    ${style}=    Get Element Attribute    ${MESSAGE_CONTAINER}    style
    Should Contain    ${style}    display: block
    ${classes}=    Get Element Attribute    ${MESSAGE_CONTAINER}    class
    Should Contain    ${classes}    show
    Sleep    1s

Create Employee And Verify
    [Arguments]    ${employee_data}
    Input Text    ${FIRST_NAME_INPUT}    ${employee_data}[firstName]
    Input Text    ${LAST_NAME_INPUT}     ${employee_data}[lastName]
    Input Text    ${EMAIL_INPUT}         ${employee_data}[email]
    Input Text    ${DEPARTMENT_INPUT}    ${employee_data}[department]
    Wait Until Element Is Enabled    ${SAVE_BTN}    timeout=30s
    Click Element    ${SAVE_BTN}
    Wait For Success Message    Employee created successfully
    Sleep    2s    # Add extra wait after success message

*** Test Cases ***
Verify Page Title
    Go To    ${FRONTEND_URL}
    ${title}=    Get Title
    Should Be Equal    ${title}    Employee Management
    Title Should Be    Employee Management

Verify Navigation
    Go To    ${FRONTEND_URL}
    Wait Until Element Is Visible    ${NAVBAR_BRAND}
    Element Text Should Be    ${NAVBAR_BRAND}    Employee Management
    Element Should Be Visible    ${ADD_EMPLOYEE_NAV}
    Element Should Be Visible    ${EMPLOYEE_LIST_NAV}
    Element Text Should Be    ${ADD_EMPLOYEE_NAV}    Add Employee
    Element Text Should Be    ${EMPLOYEE_LIST_NAV}    Employee List
