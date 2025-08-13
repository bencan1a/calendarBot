### 2.1.3 Processing Rules

Article10/13/2020

Section 2.1.3.1 specifies over 100 components, properties, and parameters that can be converted between the iCalendar and Calendar object. The following table provides recommendations regarding the actual relevance of each component, property, and parameter to the scenarios defined by five values of the METHOD property: 'PUBLISH' (PUB), 'REQUEST' (REQ), 'REPLY' (REP), 'COUNTER' (COU), and 'CANCEL' (CAN) (as specified in .

For clarity, 'No's are represented by a blank space. The '•' symbol is used to indicate hierarchy placement.

#### 2.1.3.1 Hierarchy of Components, Properties, and Parameters

Article02/14/2019

This section enumerates all iCalendar components, properties, and parameters that can be mapped to Calendar objects. The hierarchy presented in the header specifies all parent-child relationships between these components, properties, and parameters. Any components, properties, and parameters not specified in this document SHOULD be ignored.

Unless otherwise specified, if the Calendar object property being exported is not set, then the corresponding property SHOULD NOT be exported. Similarly, unless otherwise specified, if the property being imported is not present, then the corresponding Calendar object property SHOULD be left unset.

##### 2.1.3.1.1 Component: VCALENDAR

Article02/14/2019

RFC Reference: section 4.4

Number of Instances Allowed: 1+

Brief Description: The root component of a valid iCalendar file.

Importing to and Exporting from Calendar objects

A valid iCalendar file SHOULD<1> have exactly one VCALENDAR component as its root.

###### 2.1.3.1.1.1 Property: METHOD

Article04/16/2024

RFC Reference: section 4.7.2

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Distinguishes normal appointments from meeting requests, responses, and cancellations.

Importing to Calendar objects

The METHOD property SHOULD<2> be imported as the PidTagMessageClass (section  and PidLidAppointmentCounterProposal ([MS-OXPROPS] section ) of all imported Calendar objects, as specified in the table later in this section. In the case where the METHOD property is set to 'REPLY', the

PidTagMessageClass has several possible values depending on the PARTSTAT parameter

(as specified in section 2.1.3.1.1.20.2.3) of the ATTENDEE property (as specified in section

2.1.3.1.1.20.2) of the VEVENT component (as specified in section 2.1.3.1.1.20). If the METHOD property is set to 'REPLY' or 'COUNTER', the iCalendar MUST have exactly one ATTENDEE property and exactly one such PARTSTAT parameter.

In the case where the METHOD property is set to 'REQUEST', 'REPLY', or 'CANCEL', the VCALENDAR component MUST define exactly one appointment.<3>

ﾉ Expand table

Exporting from Calendar objects

For exports of calendars, the METHOD property MUST be left unset or set to 'PUBLISH'.

For exports of individual Calendar objects, the PidTagMessageClass and

PidLidAppointmentCounterProposal of the Calendar object SHOULD<4> be exported as the METHOD property as specified in the table earlier in this section.

###### 2.1.3.1.1.2 Property: PRODID

Article • 05/20/2025

RFC Reference: section 4.7.3

Number of Instances Allowed: 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Identifies the application that generated the iCalendar file.

Importing to Calendar objects

When parsing an iCalendar file, if the value of the PRODID property begins with the substring '-//Microsoft Corporation//Outlook<SP>' and ends with the substring '<SP>MIMEDIR//EN', where 'MIMEDIR' represents the Mimedir.dll file. '<SP>' represents the space character (Unicode character U+0020), the portion of the string between the two substrings SHOULD be evaluated to determine if it matches the following ABNF rule:

version_number = 1*2DIGIT '.' *DIGIT

The DIGIT elements to the left of the period ('.') are evaluated as an integer. If the integer is between 1 and 11 (inclusive), then some behavior changes SHOULD be made as described in section 2.1.3.2.4.

Exporting from Calendar objects

The value assigned to PRODID MUST be unique for different implementations or different versions of an iCalendar converter.

###### 2.1.3.1.1.3 Property: VERSION

Article02/14/2019

RFC Reference: section 4.7.4

Number of Instances Allowed: 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Identifies the version of an iCalendar file.

Importing to and Exporting from Calendar objects The value of this property MUST be set to '2.0'.

###### 2.1.3.1.1.4 Property: X-CALEND

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1, 2

Format: Date-Time (section 4.3.5)

Brief Description: Identifies the end time of the last instance of an appointment in the iCalendar file.

Importing to Calendar objects

This property SHOULD be ignored.

Exporting from Calendar objects

This property SHOULD<5> be computed as the end time of the last instance of an appointment in the iCalendar file. If the iCalendar contains appointments with floating and non-floating end times in such a way that the calendar's end time is dependent on the recipient's time zone, the X-CALEND property SHOULD<6> be declared twice: once with a floating calendar end time, and once with a non-floating calendar end time.

####### 2.1.3.1.1.4.1 Parameter: TZID

Article02/14/2019

RFC Reference: section 4.2.19

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In conjunction with a matching VTIMEZONE (as specified in section

2.1.3.1.1.19), specifies the time zone of a Date-Time property provided in local time.

###### 2.1.3.1.1.5 Property: X-CALSTART

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1, 2

Format: Date-Time (section 4.3.5)

Brief Description: Identifies the start time of the first instance of an appointment in the iCalendar file.

Importing to Calendar objects

This property SHOULD be ignored.

Exporting from Calendar objects

This property SHOULD<7> be computed as the start time of the first instance of an appointment in the iCalendar file. If the iCalendar contains appointments with floating and non-floating start times in such a way that the calendar's start time is dependent on the recipient's time zone, the X-CALSTART property SHOULD<8> be declared twice: once with a floating calendar start time, and once with a non-floating calendar start time.

####### 2.1.3.1.1.5.1 Parameter: TZID

Article02/14/2019

RFC Reference: section 4.2.19

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In conjunction with a matching VTIMEZONE, specifies the time zone of a Date-Time property provided in local time.

###### 2.1.3.1.1.6 Property: X-CLIPEND

Article08/17/2021

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Date-Time (section 4.3.5)

Brief Description: Indicates the end of the date range that the user selected for export during the creation of the iCalendar file.

Importing to Calendar objects

This property SHOULD<9> be ignored.

Exporting from Calendar objects

This property SHOULD<10> be the end of the date range that the user selected for export. If this iCalendar does not represent a calendar export, this property MUST be omitted.

####### 2.1.3.1.1.6.1 Parameter: TZID

Article02/14/2019

RFC Reference: section 4.2.19

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In conjunction with a matching VTIMEZONE, specifies the time zone of a Date-Time property provided in local time.

###### 2.1.3.1.1.7 Property: X-CLIPSTART

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Date-Time (section 4.3.5)

Brief Description: Indicates the start of the date range that the user selected for export during the creation of the iCalendar file.

Importing to Calendar objects

This property SHOULD<11> be ignored.

Exporting from Calendar objects

This property SHOULD<12> be the start of the date range that the user selected for export. If this iCalendar does not represent a calendar export, this property MUST be omitted.

####### 2.1.3.1.1.7.1 Parameter: TZID

Article02/14/2019

RFC Reference: section 4.2.19

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In conjunction with a matching VTIMEZONE, specifies the time zone of a Date-Time property provided in local time.

###### 2.1.3.1.1.8 Property: X-MICROSOFTCALSCALE

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0,1

Format: Text (section 4.3.11)

Brief Description: Identifies the calendar type of a non-Gregorian recurring appointment.

Importing to Calendar objects

If this property is specified, then it SHOULD<13> be imported for every VEVENT that declares an X-MICROSOFT-RRULE.

This property SHOULD<14> set the CalendarType field of the RecurrencePattern field of the AppointmentRecurrencePattern structure ( section ) in the PidLidAppointmentRecur property ([MS-OXOCAL] section ). See also sections 2.1.3.2.2.1, 2.1.3.2.2.2, 2.1.3.2.2.3, 2.1.3.2.2.4, 2.1.3.2.2.5, and 2.1.3.2.2.6.

For appointments with an X-MICROSOFT-CALSCALE value of "Hijri", the value for PatternType (as specified in [MS-OXOCAL] section  and CalendarType depend upon the imported value of PatternType. PatternType SHOULD be determined as specified in section 2.1.3.2.2. The resulting value SHOULD then be overwritten as specified in the following table.

Exporting from Calendar objects

Since this property is a child of the VCALENDAR, a VCALENDAR MUST NOT contain any two VEVENTs that would result in different values of X-MICROSOFT-CALSCALE.

If the CalendarType field of the RecurrencePattern field of the

AppointmentRecurrencePattern structure is nonzero, then this property SHOULD<16> be exported as specified in the following table.

Additionally, for certain values of the PatternType field of the RecurrencePattern field of the AppointmentRecurrencePattern structure, this property SHOULD<17> be exported as specified in the following table.

2.1.3.1.1.9 Property: X-MS-OLK-

# CALENDAR

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Boolean (section 4.3.2)

Brief Description: Specifies whether or not the iCalendar file represents a primary calendar.

Importing to Calendar objects

This property SHOULD<30> be ignored.

Exporting from Calendar objects

If this iCalendar does not represent the primary calendar of the owner, this property SHOULD be omitted. Otherwise, this property SHOULD<31> be set to 'TRUE'.

## 2.1.3.1.1.15 Property: X-PUBLISHED-TTL

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Duration ( section 4.3.6)

Brief Description: Specifies a suggested iCalendar file download frequency for clients and servers with sync capabilities.

Importing to Calendar objects

This property SHOULD<32> be ignored.

Exporting from Calendar objects

If this iCalendar is being automatically published to a remote location at regular intervals, this property SHOULD<33> be set to that interval with a minimum granularity of minutes.

## 2.1.3.1.1.16 Property: X-WR-CALDESC

Article08/17/2021

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Specifies the description of the calendar.

Importing to Calendar objects

This property SHOULD<34> be ignored.

Exporting from Calendar objects

If this iCalendar represents an export of a calendar, and if the owner has provided a description of the calendar, this property SHOULD<35> be set to the owner's specified text, which SHOULD<36> be truncated to a length of 255 WCHARs if the length exceeds

255 WCHARs. The truncation SHOULD NOT<37> split surrogate pairs (as specified in  section 2.5).

## 2.1.3.1.1.17 Property: X-WR-CALNAME

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Specifies the name of the calendar.

Importing to Calendar objects

destination of the imported appointments. Implementations MAY truncate the value to 255 characters and MAY remove carriage return (Unicode character U+000D) and line feed (Unicode character U+000A) characters.

Exporting from Calendar objects

This property MUST be omitted if the iCalendar represents a single appointment or meeting.

If this iCalendar represents a calendar export, this property SHOULD<39> be set to the value of PidTagDisplayName on the Folder object representing the calendar being exported.

If the calendar is the owner's primary calendar, this property SHOULD<40> instead be set to a more descriptive locale-dependent string containing the owner's name (e.g.

'Elizabeth Andersen calendar').

## 2.1.3.1.1.18 Property: X-WR-RELCALID

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Specifies a globally unique identifier for the calendar.

Importing to Calendar objects

This property SHOULD<41> be used and persisted by the iCalendar renderer to decide whether the import overwrites an existing calendar or creates a new calendar.

Exporting from Calendar objects

This property MUST be omitted if the iCalendar represents a single appointment or meeting.

If this iCalendar represents a calendar export, this property SHOULD<42> be set to a value that will be globally unique for different calendars, but consistent across multiple exports of the same calendar.

## 2.1.3.1.1.19 Component: VTIMEZONE

Article08/17/2021

RFC Reference: section 4.6.5

Number of Instances Allowed: 0+<43>

Brief Description: Specifies any time zones referenced by TZID parameters.

Importing to Calendar objects

Since TZIDs can be referenced by many properties in the root component, VTIMEZONEs MUST be used to resolve all local times in the iCalendar file, even if the TZID reference occurs before the VTIMEZONE definition. This section discusses how to import a VTIMEZONE into a PidLidTimeZoneStruct structure ( section .

OXPROPS] section ), and/or PidLidAppointmentTimeZoneDefinitionEndDisplay ([MS-OXPROPS] section ),<44> then the following table specifies the contents of the resulting BLOB (the structure of this BLOB is specified in [MS-OXOCAL]). See section

2.1.3.1.1.20.8.1 and section 2.1.3.1.1.20.10.1 for more information.

The following table specifies the contents of each TZRule structure in the TZRules field.

Exporting from Calendar objects

A VTIMEZONE component MUST be declared for each unique value of any TZID parameters in the iCalendar. Note that the comparison used to match TZID parameters to VTIMEZONE components SHOULD<46> be case-insensitive.

If exporting a VTIMEZONE from a PidLidAppointmentTimeZoneDefinitionRecur,

PidLidAppointmentTimeZoneDefinitionStartDisplay, or

PidLidAppointmentTimeZoneDefinitionEndDisplay, the lBias, lStandardBias, lDaylightBias, stStandardDate, and stDaylightDate subfields of the TZRule entry with the TZRULE_FLAG_EFFECTIVE_TZREG (0x0002) bit set in the TZRule flags field MUST be exported as a PidLidTimeZoneStruct structure as specified in the following subsections.

<47>

### 2.1.3.1.1.19.1 Property: TZID

Article02/14/2019

RFC Reference: section 4.8.3.1

Number of Instances Allowed: 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: The name of the time zone. This string will be compared (caseinsensitive)<48> to TZID parameters in the rest of the iCalendar to identify the time zone being referenced by the parameter's parent property.

Importing to Calendar objects

This property SHOULD be imported as specified in section 2.1.3.1.1.20.8.1 and section

2.1.3.1.1.20.10.1.

Exporting from Calendar objects

If the system's local time zone is being exported as a VTIMEZONE, then this name MUST be derived from the system API that supplied the time zone.

If the PidLidTimeZoneStruct property is being exported as a VTIMEZONE, this name SHOULD be derived from PidLidTimeZoneDescription (section ), but MAY be set to any unique string.

If the PidLidAppointmentTimeZoneDefinitionRecur,

PidLidAppointmentTimeZoneDefinitionStartDisplay, or

PidLidAppointmentTimeZoneDefinitionEndDisplay property is being exported as a VTIMEZONE, then the value of TZID MUST<49> be derived from the KeyName field of the PidLidAppointmentTimeZoneDefinitionRecur structure ([MS-OXOCAL] section

contained in the property.

In all cases, TZIDs for different time zones MUST be unique, and each unique TZID MUST NOT be defined more than once.

### 2.1.3.1.1.19.2 Component: STANDARD

Article08/17/2021

RFC Reference: section 4.6.5

Number of Instances Allowed: 1+

Brief Description: A specification of the Standard portion of the time zone.

Importing to Calendar objects

If more than one STANDARD component is defined in the VTIMEZONE, only the

STANDARD component with the largest DTSTART (as specified in section 2.1.3.1.1.19.2.1)

SHOULD<50> be parsed. Alternatively, implementers MAY<51> parse the first STANDARD component found within the VTIMEZONE, MAY<52> parse all STANDARD components found within the VTIMEZONE that have unique years in their DTSTART subcomponents, or MAY<53> fail to parse the iCalendar stream if more than one STANDARD component is defined in the VTIMEZONE.

Exporting from Calendar objects

Exactly one STANDARD component SHOULD be exported for each VTIMEZONE.

#### 2.1.3.1.1.19.2.1 Property: DTSTART

Article08/17/2021

RFC Reference: section 4.8.2.4

Number of Instances Allowed: 1

Format: Date-Time ([RFC2445] section 4.3.5)

Brief Description: The effective start date of this onset of Standard time.

Importing to Calendar objects

If this VTIMEZONE component has no DAYLIGHT sub-component, all the bytes in the stStandardDate field of the PidLidTimeZoneStruct structure MUST be set to 0x00.

If the VTIMEZONE being imported contains one or more DAYLIGHT sub-components and the STANDARD component contains an RRULE property (as specified in section 2.1.3.1.1.19.2.2), the fields of the stStandardDate field of the PidLidTimeZoneStruct structure are set according to the following table.

If an RRULE property is not specified for this component, the stStandardDate field of the PidLidTimeZoneStruct structure SHOULD<54> be imported as specified in the following table. Alternatively, implementers MAY<55> convert the value of the RDATE property to a SYSTEMTIME structure (as specified in  and import the resulting value to the stStandardDate field, or MAY<56> convert the value of the DTSTART property to a SYSTEMTIME structure and import the resulting value to the stStandardDate field.

The following table lists the possible values of the wDayOfWeek subfield of the stStandardDate field in the PidLidTimeZoneStruct structure.

The following table lists the possible values of the wDay subfield of the stStandardDate field in the PidLidTimeZoneStruct structure.

Exporting from Calendar objects

This MUST be set to the onset of the Standard portion of the time zone for some year before the first appointment in the iCalendar.<57> This property is specified in the local time of the VTIMEZONE component, but the TZID parameter of this property is omitted.

#### 2.1.3.1.1.19.2.2 Property: RRULE

Article10/13/2020

RFC Reference: section 4.8.5.4

Number of Instances Allowed: 0,1

Format: Recurrence rule ([RFC2445] section 4.3.10)

Brief Description: A rule describing the onset of Standard time for years following DTSTART.

Importing to Calendar objects

If this VTIMEZONE component has no DAYLIGHT sub-component, all the bytes in the stStandardDate field of the PidLidTimeZoneStruct structure MUST be set to 0x00 (as specified in 2.1.3.1.1.19.2.1). The remainder of this subsection only pertains to the case where the VTIMEZONE being imported contains one or more DAYLIGHT subcomponents.

For basic information regarding the Recurrence rule format, see [RFC2445] section 4.3.10 and section 2.1.3.2.1 of this document.

Time zone recurrences MUST be of frequency YEARLY and MUST specify either a BYDAY or a BYMONTHDAY, but not both.

If a BYDAY is specified, it MUST specify a single occurrence of a single day of the week (e.g. BYDAY=2MO, but not BYDAY=MO or BYDAY=1MO,3MO). The recurrence is imported into the stStandardDate field of the PidLidTimeZoneStruct structure using the following table.

If a BYMONTHDAY is specified, it MUST specify a single day of the month

(BYMONTHDAY=12, but not BYMONTHDAY=14,15). The recurrence SHOULD<58> be imported into the stStandardDate field of the PidLidTimeZoneStruct structure as specified in the following table.

Exporting from Calendar objects

For basic information regarding the Recurrence rule format, see [RFC2445] section 4.3.10 and section 2.1.3.2.1 of this document.

If the time zone does not observe Daylight Saving Time (DST), this property MUST be omitted.

If the time zone transitions between Daylight Saving Time and Standard Time based on an occurrence of a day of the week, this property MUST be of the form FREQ=YEARLY;BYDAY=byday;BYMONTH=bymonth.

If the time zone transitions between Daylight Saving Time and Standard Time based on a specific day of the month, this property SHOULD<59> be of the form FREQ=YEARLY;BYMONTHDAY=bymonthday;BYMONTH=bymonth.

#### 2.1.3.1.1.19.2.3 Property: TZNAME

Article02/14/2019

RFC Reference: section 4.8.3.2

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: The name of the standard portion of the time zone.

Importing to Calendar objects

This property SHOULD be ignored on import.

Exporting from Calendar objects

This property SHOULD<60> be omitted.

#### 2.1.3.1.1.19.2.4 Property: TZOFFSETFROM

Article02/14/2019

RFC Reference: section 4.8.3.3

Number of Instances Allowed: 1

Format: UTC-Offset ([RFC2445] section 4.3.14)

Brief Description: The UTC-Offset of the Daylight portion of the time zone.

Importing to Calendar objects

This property SHOULD be ignored on import.

Exporting from Calendar objects

This property MUST be the UTC-Offset representation of (-1 *

(PidLidTimeZoneStruct.lBias + PidLidTimeZoneStruct.lDaylightBias)).

#### 2.1.3.1.1.19.2.5 Property: TZOFFSETTO

Article02/14/2019

RFC Reference: section 4.8.3.4

Number of Instances Allowed: 1

Format: UTC-Offset ([RFC2445] section 4.3.14)

Brief Description: The UTC-Offset of the Standard portion of the time zone.

Importing to Calendar objects

The lBias field of the PidLidTimeZoneStruct structure MUST be set to (-1 * offsetMinutes), where offsetMinutes is the value of TZOFFSETTO in minutes.

Exporting from Calendar objects

This property MUST be the UTC-Offset representation of (-1 *

(PidLidTimeZoneStruct.lBias + PidLidTimeZoneStruct.lStandardBias)).

### 2.1.3.1.1.19.3 Component: DAYLIGHT

Article04/16/2024

RFC Reference: section 4.6.5

Number of Instances Allowed: 0+

Brief Description: A specification of the Daylight portion of the time zone.

Importing to Calendar objects

If more than one DAYLIGHT component is defined in the VTIMEZONE, only the DAYLIGHT component with the largest DTSTART SHOULD<61> be parsed. Alternatively, implementers MAY<62> parse the first DAYLIGHT component found within the VTIMEZONE, MAY<63> parse all STANDARD components found within the VTIMEZONE that have unique years in their DTSTART subcomponents, or MAY<64> fail to parse the iCalendar stream if more than one DAYLIGHT component is defined in the VTIMEZONE.

If no DAYLIGHT components are defined in the VTIMEZONE then all the bytes in the lDaylightBias, lStandardBias, stDaylightDate, and stStandardDate fields of the PidLidTimeZoneStruct MUST be set to 0x00.

Exporting from Calendar objects

If this time zone observes Daylight Saving Time, exactly one DAYLIGHT component MUST be exported for each VTIMEZONE.

If this time zone does not observe DST, this component SHOULD<65> be omitted.

#### 2.1.3.1.1.19.3.1 Property: DTSTART

Article02/14/2019

RFC Reference: section 4.8.2.4

Number of Instances Allowed: 1

Format: Date-Time ([RFC2445] section 4.3.5)

Brief Description: The effective start date of this onset of Daylight Saving Time.

Importing to and Exporting from Calendar objects

The behavior of this property is identical to the behavior of the DTSTART property of the STANDARD component (section 2.1.3.1.1.19.2.1) with the exception that stDaylightDate is modified instead of stStandardDate.

#### 2.1.3.1.1.19.3.2 Property: RRULE

Article08/17/2021

RFC Reference: section 4.8.5.4

Number of Instances Allowed: 0,1

Format: Recurrence rule ([RFC2445] section 4.3.10)

Brief Description: A rule describing the onset of Daylight Saving Time for years following DTSTART.

Importing to and Exporting from Calendar objects

The behavior of this property is identical to the behavior of the RRULE property of the STANDARD component (section 2.1.3.1.1.19.2.2) with the exception that stDaylightDate is modified instead of stStandardDate.

#### 2.1.3.1.1.19.3.3 Property: TZNAME

Article02/14/2019

RFC Reference: section 4.8.3.2

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: The name of the daylight portion of the time zone.

Importing to Calendar objects

This property MUST be ignored on import.

Exporting from Calendar objects

This property SHOULD<66> be omitted.

#### 2.1.3.1.1.19.3.4 Property: TZOFFSETFROM

Article02/14/2019

RFC Reference: section 4.8.3.3

Number of Instances Allowed: 1

Format: UTC-Offset ([RFC2445] section 4.3.14)

Brief Description: The UTC-Offset of the Standard portion of the time zone.

Importing to Calendar objects

This property SHOULD be ignored on import.

Exporting from Calendar objects

This property MUST be the UTC-Offset representation of (-1 *

(PidLidTimeZoneStruct.lBias + PidLidTimeZoneStruct.lStandardBias)).

#### 2.1.3.1.1.19.3.5 Property: TZOFFSETTO

Article08/17/2021

RFC Reference: section 4.8.3.4

Number of Instances Allowed: 1

Format: UTC-Offset ([RFC2445] section 4.3.14)

Brief Description: The UTC-Offset of the Daylight portion of the time zone.

Importing to Calendar objects

The lDaylightBias field of PidLidTimeZoneStruct structure MUST be set to (-1 * offsetMinutes - lBias), where offsetMinutes is the value of TZOFFSETTO measured in minutes.

Exporting from Calendar objects

This property MUST be the UTC-Offset representation of (-1 *

(PidLidTimeZoneStruct.lBias + PidLidTimeZoneStruct.lDaylightBias)).

## 2.1.3.1.1.20 Component: VEVENT

Article02/14/2019

RFC Reference: section 4.6.1

Number of Instances Allowed: 1+

Brief Description: A specification of an appointment or an exception to a recurring appointment.

Importing to Calendar objects

With the exception of those containing RECURRENCE-ID properties (section

2.1.3.1.1.20.20), all VEVENT components MUST map to a new Calendar object.

Exporting from Calendar objects

Each Calendar object MUST be exported to its own VEVENT component. Certain exceptions to recurring appointments can also be exported as separate VEVENT components as specified in section 2.1.3.1.1.20.20.

### 2.1.3.1.1.20.1 Property: ATTACH

Article08/17/2021

RFC Reference: section 4.8.1.1

Number of Instances Allowed: 0+

Format: URI ([RFC2445] section 4.3.13), Binary ([RFC2445] section 4.3.1) Brief Description: An attachment to the appointment.

Importing to Calendar objects

If the VALUE parameter (as specified in section 2.1.3.1.1.20.1.3) of this property is

BINARY, then this property SHOULD<67> be parsed as a stream encoded with base64 encoding (as specified in  section 6.8), decoded into its raw binary form, and stored in PidTagAttachDataBinary (section  of a new Attachment object with properties specified in the following table.

If the VALUE parameter of this property is "URI" or not defined, then this property SHOULD<68> be parsed as a URI. CID URIs (as specified in ) SHOULD<69> be used, for the case in which the iCalendar is embedded in a multi-part MIME e-mail to determine which attachments from the MIME will be imported into the Calendar object. Other URIs SHOULD<70> be imported into a new Attachment object with properties specified in the following table.

Exporting from Calendar objects

If this iCalendar is being generated as part of a MIME meeting request, all attachments in the attachments table that meet the constraints in the following table SHOULD<71> be exported as a CID URI (as specified in [RFC2392]). In this case, the value of this property MUST be a CID URI generated by treating PidTagAttachContentId ([MS-

OXPROPS] section  as a CID. If PidTagAttachContentId does not exist, an

[RFC2392]-compliant CID SHOULD<72> be generated and stored in PidTagAttachContentId.

If this iCalendar is being generated as part of a calendar export, all attachments in the attachments table that meet the constraints in the following table SHOULD<73> be exported as binary streams encoded with base64 encoding. The value of this property MUST be the base64 encoding of PidTagAttachDataBinary (base64 encoding is specified in [RFC2045] section 6.8).

#### 2.1.3.1.1.20.1.1 Parameter: ENCODING

Article02/14/2019

RFC Reference: section 4.2.7

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the encoding of a binary attachment.

Importing to and Exporting from Calendar objects

If the VALUE parameter of this ATTACH is BINARY, then the value of this parameter MUST be "base64". Otherwise, this parameter MUST be omitted.

#### 2.1.3.1.1.20.1.2 Parameter: FMTTYPE

Article02/14/2019

RFC Reference: section 4.2.8

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the MIME content type of an attachment.

Importing to Calendar objects

This parameter SHOULD<74> be imported as PidTagAttachMimeTag.

Exporting from Calendar objects

This parameter MAY take the value of PidTagAttachMimeTag.

#### 2.1.3.1.1.20.1.3 Parameter: VALUE

Article02/14/2019

RFC Reference: section 4.2.20

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Distinguishes encoded binary attachments from URI attachments.

Importing to Calendar objects

This parameter distinguishes attachments encoded in the iCalendar from URIs referencing resources outside the iCalendar. See section 2.1.3.1.1.20.1.

Exporting from Calendar objects

If this iCalendar is being generated as part of a MIME meeting request, this parameter SHOULD be omitted.

If this iCalendar is being generated as part of a calendar export, this parameter SHOULD be BINARY.

#### 2.1.3.1.1.20.1.4 Parameter: X-FILENAME

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Supplies a filename for an encoded binary attachment.

Importing to Calendar objects

If the VALUE parameter of this ATTACH is BINARY, this X-FILENAME parameter SHOULD<75> be sanitized as specified in section and imported as PidTagAttachFilename, PidTagAttachLongFilename, and

PidTagDisplayName. The filename extension parsed from this parameter is imported as PidTagAttachExtension as specified in section 2.1.3.1.1.20.1.

Otherwise, the X-FILENAME parameter is ignored.

Exporting from Calendar objects

If the VALUE parameter of this ATTACH is BINARY, then this parameter SHOULD<76> take the value of PidTagAttachLongFilename.

Otherwise, this parameter SHOULD be omitted.

### 2.1.3.1.1.20.2 Property: ATTENDEE

Article10/13/2020

RFC Reference: section 4.8.4.1

Number of Instances Allowed: 0+

Format: Calendar User Address ([RFC2445] section 4.3.3) Brief Description: An attendee for a meeting.

Importing to Calendar objects

If this property has the special value 'invalid:nomail', then the CN of this attendee SHOULD<77> be added to a list delimited by "; " (Unicode character U+003B followed by U+0020) in the appropriate string property, as specified in the following table. If an attendee matches more than one row in the following table, the first matching row applies.

If this property is not 'invalid:nomail', it SHOULD<80> be parsed as a valid mailto URI (as specified in . The resulting SMTP address SHOULD<81> be resolved parameter. The Address Book object MUST be added to the recipient table of the Calendar object with properties specified in the following table.

The correct value of PidTagRecipientType SHOULD<89> be determined based on the CUTYPE and ROLE (as specified in section 2.1.3.1.1.20.2.4) parameters as specified in the following table. If an attendee matches more than one row in the following table, the first matching row applies.

Exporting from Calendar objects

If the 0x00000001 flag of PidLidAppointmentStateFlags ([MS-OXPROPS] section  is 0, then attendee properties SHOULD NOT<91> be exported.

Each row in the recipient table of the Calendar object that satisfies the constraints in the following table MUST be exported as an attendee property. The value of the property MUST be a mailto URI (as specified in [RFC2368]) with the SMTP address of the recipient from the address book [MS-OXOABK]. If the recipient does not have an SMTP address, then the value of the property SHOULD<92> be set to 'invalid:nomail'.

In addition, each of the semicolon-delimited entries in PidLidNonSendableTo and PidLidNonSendableCc SHOULD<93> be exported with a URI of 'invalid:nomail'. For handling of PidLidNonSendableBcc, see 2.1.3.1.1.20.21.

#### 2.1.3.1.1.20.2.1 Parameter: CN

Article02/14/2019

RFC Reference: section 4.2.2

Number of Instances Allowed: 0,1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: The display name of an attendee.

Importing to Calendar objects See section 2.1.3.1.1.20.2.2.

Exporting from Calendar objects

For attendees exported from the recipient table, this parameter SHOULD be exported from the PidTagDisplayName from the Address Book object (falling back on the PidTagDisplayName from the recipient table, if necessary).

For attendees exported from PidLidNonSendableTo and PidLidNonSendableCc, this parameter SHOULD<94> be taken from the semicolon-delimited lists.

#### 2.1.3.1.1.20.2.2 Parameter: CUTYPE

Article02/14/2019

RFC Reference: section 4.2.3

Number of Instances Allowed: 0,1 Format: Text ([RFC2445] section 4.3.11)

Brief Description: The type of attendee.

Importing to Calendar objects See section 2.1.3.1.1.20.2.

Exporting from Calendar objects

For attendees exported from the recipient table, this parameter SHOULD<95> only be exported if the PidTagRecipientType is 0x00000003. In this case, the CUTYPE SHOULD<96> be set to "RESOURCE".

For attendees exported from PidLidNonSendableTo and PidLidNonSendableCc, this parameter SHOULD be omitted.

#### 2.1.3.1.1.20.2.3 Parameter: PARTSTAT

Article • 05/20/2025

RFC Reference: section 4.2.12

Number of Instances Allowed: 0,1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: The attendee's response status.

Importing to Calendar objects

Import behavior for the PARTSTAT parameter into the recipient table is specified in section

2.1.3.1.1.20.2.

For calendars with a METHOD of COUNTER or REPLY, the PARTSTAT parameter is used in conjunction with the METHOD property to determine the PidTagMessageClass of the Calendar object. See section 2.1.3.1.1.1.

For calendars with a METHOD of PUBLISH, if the attendee is the user, the PARTSTAT parameter SHOULD<97> also be imported to the PidLidResponseStatus ( section ) of the Calendar object as follows.

ﾉ Expand table

Exporting from Calendar objects

For calendars with a METHOD of COUNTER or REPLY, the PARTSTAT parameter MUST be exported based on the PidTagMessageClass of the Calendar object. See section 2.1.3.1.1.1.

For calendars with a METHOD of PUBLISH, if the attendee is being exported from a row in the recipient table, the PARTSTAT parameter SHOULD<98> be exported from the

PidTagRecipientTrackStatus of the recipient as specified in the following table. If

PidTagRecipientTrackStatus could not be exported because it is unset or 0 and the attendee is the user, then the PidLidResponseStatus of the Calendar object SHOULD<99> be exported instead as specified in the following table.

ﾉ Expand table

#### 2.1.3.1.1.20.2.4 Parameter: ROLE

Article10/13/2020

RFC Reference: section 4.2.16

Number of Instances Allowed: 0,1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: The participation role of the attendee.

Importing to Calendar objects See section 2.1.3.1.1.20.2.

Exporting from Calendar objects

For ATTENDEES exported from the recipient table, this parameter SHOULD be exported based on the PidTagRecipientType, as specified in the following table.

For ATTENDEES exported from PidLidNonSendableTo, this parameter SHOULD be omitted.

For ATTENDEES exported from PidLidNonSendableCc, this parameter SHOULD<101> be exported as OPT-PARTICIPANT.

#### 2.1.3.1.1.20.2.5 Parameter: RSVP

Article • 03/18/2025

RFC Reference: section 4.2.17

Number of Instances Allowed: 0,1

Format: Boolean ([RFC2445] section 4.3.2)

Brief Description: To specify whether there is an expectation of a reply from this attendee.

Importing to Calendar objects

If any ATTENDEE property in the VEVENT has its RSVP parameter set to TRUE or if the

VEVENT is being imported with a PidTagMessageClass of "IPM.Appointment", then

PidTagResponseRequested (section  and PidTagReplyRequested ([MS-OXPROPS] section  on the Calendar object MUST both be set to TRUE. Otherwise, PidTagResponseRequested and PidTagReplyRequested MUST both be set to FALSE.

Exporting from Calendar objects

For ATTENDEES exported from the recipient table, this parameter MUST be exported from PidTagResponseRequested on the Calendar object.

For ATTENDEES exported from PidLidNonSendableTo and PidLidNonSendableCc, this parameter SHOULD be omitted.

#### 2.1.3.1.1.20.2.6 Parameter: X-MS-OLKRESPTIME

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Date-Time (section 4.3.5), Date ([RFC2445] section 4.3.4)

Brief Description: The time that the ATTENDEE responded to the meeting request.

Importing to Calendar objects

Section 2.1.3.1.1.20.2 specifies how X-MS-OLK-RESPTIME is imported into the recipient table.

For calendars with a METHOD of PUBLISH, if the attendee is the user, the X-MS-OLKRESPTIME parameter SHOULD also be imported to the PidLidAppointmentReplyTime

(section ) of the Calendar object.<102>

Exporting from Calendar objects

For calendars with a METHOD of PUBLISH, if the attendee is being exported from a row in the recipient table, the X-MS-OLK-RESPTIME parameter MAY be exported in UTC format from the PidTagRecipientTrackStatusTime of the recipient. If

PidTagRecipientTrackStatus could not be exported as specified in section 2.1.3.1.1.20.2.3 because it is unset or 0 and the attendee is the user, the PidLidAppointmentReplyTime of the Calendar object SHOULD be exported in UTC format instead.<103>

### 2.1.3.1.1.20.3 Property: CATEGORIES

Article08/17/2021

RFC Reference: section 4.8.1.2

Number of Instances Allowed: 0+

Format: Text ([RFC2445] section 4.3.11)

Brief Description: A list of categories assigned to the appointment.

Importing to Calendar objects

All instances of the CATEGORIES property SHOULD be parsed into a single array of strings. Several rules apply to the import of categories:

All separator characters, semicolon (Unicode character U+003B), comma (Unicode character U+002C), Arabic semicolon (Unicode character U+061B), small semicolon

(Unicode character U+FE54), full-width semicolon (Unicode character U+FF1B), SHOULD<104> be removed.

All contiguous sequences of whitespace<105> characters SHOULD<106> be truncated to a single space (Unicode character U+0020) character.

Whitespace at the start and end of each string SHOULD be trimmed.

Strings SHOULD<107> be truncated to a length of 255 WCHARs if the length exceeds 255 WCHARs, but the truncation SHOULD NOT<108> split surrogate pairs.

All case-insensitive duplicate occurrences and zero-length strings in the array SHOULD<109> be removed.

The resulting string array is stored in PidNameKeywords ( section ).

Exporting from Calendar objects

PidNameKeywords SHOULD be exported as a comma-delimited list in the CATEGORIES property.

### 2.1.3.1.1.20.4 Property: CLASS

Article10/13/2020

RFC Reference: section 4.8.1.3

Number of Instances Allowed: 0,1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: The privacy or classification level of an appointment.

Importing to and Exporting from Calendar objects

The CLASS property MUST map to PidTagSensitivity (section  as specified in the following table.

### 2.1.3.1.1.20.5 Property: COMMENT

Article10/13/2020

RFC Reference: section 4.8.1.4 and  section 3.2.3

Number of Instances Allowed: 0,1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In a meeting response, this property represents an optional plain-text message from the attendee intended for the organizer.

Importing to and Exporting from Calendar objects

If the METHOD property of the VCALENDAR component is set to 'REPLY' or 'COUNTER', this property SHOULD<112> be mapped directly to PidTagBody section . The COMMENT property SHOULD be ignored for other values of METHOD.

Also see the documentation for DESCRIPTION in section 2.1.3.1.1.20.11.

### 2.1.3.1.1.20.6 Property: CONTACT

Article04/16/2024

RFC Reference: section 4.8.4.2

Number of Instances Allowed: 0+

Format: Text ([RFC2445] section 4.3.11)

Brief Description: A contact for an appointment.

Importing to Calendar objects

All instances of the CONTACT property SHOULD<113> be appended to single array of strings. Several rules apply to the import of contacts.

All semicolons (Unicode character U+003B) SHOULD<114> be removed.

All contiguous sequences of whitespace<115> characters SHOULD<116> be truncated to a single space (Unicode character U+0020) character.

Whitespace at the start and end of each string SHOULD<117> be trimmed.

Strings SHOULD<118> be truncated to a length of 500 WCHARs if their length exceeds 500 WCHARs, but the truncation SHOULD NOT<119> split surrogate pairs.

All case-insensitive duplicate occurrences and zero-length strings in the array SHOULD<120> be removed.

The resulting string array is stored in PidLidContacts (section ).

Exporting from Calendar objects

Each string in the array of strings in PidLidContacts SHOULD<121> be exported as a new CONTACT property.

### 2.1.3.1.1.20.7 Property: CREATED

Article04/16/2024

RFC Reference: section 4.8.7.1

Number of Instances Allowed: 0, 1

Format: Date-Time ([RFC2445] section 4.3.5)

Brief Description: The creation time of an appointment.

Importing to Calendar objects

This property SHOULD be ignored.

Exporting from Calendar objects

The PidTagCreationTime (section  of a Calendar object SHOULD<122> be exported as a CREATED property, specified in UTC.

### 2.1.3.1.1.20.8 Property: DTEND

Article • 05/20/2025

RFC Reference: section 4.8.2.2

Number of Instances Allowed: 1

Format: Date-Time ([RFC2445] section 4.3.5), Date ([RFC2445] section 4.3.4)

Brief Description: The end time of an appointment. If the item is a counter proposal, then this is the proposed end time of the meeting.

Importing to Calendar objects

If the METHOD property of the VCALENDAR component is set to 'COUNTER', then this property

SHOULD be imported as PidLidAppointmentProposedEndWhole (section ).<123>

If the METHOD property of the VCALENDAR component is not set to 'COUNTER', or if either X-

MS-OLK-ORIGINALEND or X-MS-OLK-ORIGINALSTART is not specified, then this property SHOULD<124> be imported as PidLidAppointmentEndWhole ([MS-OXPROPS] section ), and PidLidAppointmentDuration ([MS-OXPROPS] section  SHOULD<125> be set to the number of minutes between DTSTART and DTEND.

If DTSTART and DTEND are both specified in floating time, and if both occur at midnight of their respective days, then the appointment SHOULD<126> be imported as an all-day appointment: PidLidAppointmentSubType ([MS-OXPROPS] section ) MUST be set to 0x00000001. Note that this logic SHOULD<127> also be triggered by X-MICROSOFT-CDOALLDAYEVENT (section 2.1.3.1.1.20.28) and X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT

(section 2.1.3.1.1.20.41).

Exporting from Calendar objects

If the METHOD property of the VCALENDAR component is set to 'COUNTER', then PidLidAppointmentProposedEndWhole SHOULD<128> be exported as a new DTEND property. For other values of METHOD, the PidLidAppointmentEndWhole of a Calendar object SHOULD<129> be exported as a new DTEND property.

If this is an all-day appointment, then this property SHOULD<130> be exported in floating time with the Date format ([RFC2445] section 4.3.4).

If this is a recurring non-all-day appointment, then this property MUST be specified as a local time with a TZID parameter.

Non-recurring non-all-day appointments SHOULD<131> be specified as a local time with a TZID parameter.

#### 2.1.3.1.1.20.8.1 Parameter: TZID

Article02/14/2019

RFC Reference: section 4.2.19

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In conjunction with a matching VTIMEZONE, specifies the time zone of a Date-Time property provided in local time.

Importing to Calendar objects

If this appointment is recurring, and if there is a TZID parameter, and if neither

PidLidTimeZoneStruct nor PidLidTimeZoneDescription has been imported from DTSTART (section 2.1.3.1.1.20.10), then PidLidTimeZoneStruct MUST be imported from the VTIMEZONE referenced by the TZID parameter,  PidLidTimeZoneDescription MUST be imported from the TZID parameter, and

PidLidAppointmentTimeZoneDefinitionRecur SHOULD<132> be imported from the VTIMEZONE referenced by the TZID parameter. Otherwise, this parameter SHOULD be ignored.

Furthermore, PidLidAppointmentTimeZoneDefinitionEndDisplay SHOULD<133> be imported from the VTIMEZONE referenced by the TZID parameter.

Refer to [RFC2445] section 4.2.19 for additional details on the TZID parameter.

Exporting from Calendar objects

If this is a recurring non-all-day appointment, then the DTEND property MUST be specified as a local time. It MUST be accompanied by a TZID parameter that is equal to the TZID property of the VTIMEZONE described by

PidLidAppointmentTimeZoneDefinitionRecur<134> or the combination of PidLidTimeZoneDescription and PidLidTimeZoneStruct.

If this is a non-recurring non-all-day appointment and if

PidLidAppointmentTimeZoneDefinitionEndDisplay is set, then the DTEND property SHOULD<135> be specified as a local time. It MUST be accompanied by a TZID parameter that is equal to the TZID property of the VTIMEZONE described by PidLidAppointmentTimeZoneDefinitionEndDisplay.

#### 2.1.3.1.1.20.8.2 Parameter: VALUE

Article • 05/20/2025

RFC Reference: section 4.2.20

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the format of this property.

Importing to Calendar objects

This parameter SHOULD<136> be ignored since a parser can determine whether a property is in the Date format ([RFC2445] section 4.3.4) or Date-Time format ([RFC2445] section 4.3.5) without an explicit declaration in the VALUE parameter.

Exporting from Calendar objects

If the DTEND property is specified in the Date format ([RFC2445] section 4.3.4), the VALUE parameter MUST be exported as 'DATE'. If the DTEND property is specified in the Date-Time format ([RFC2445] section 4.3.5), the VALUE parameter SHOULD be omitted, but MAY be exported as 'DATE-TIME'.

### 2.1.3.1.1.20.9 Property: DTSTAMP

Article10/13/2020

RFC Reference: section 4.8.7.2

Number of Instances Allowed: 1

Format: Date-Time ([RFC2445] section 4.3.5), Date ([RFC2445] section 4.3.4) Brief Description: The creation time of the iCalendar.

Importing to Calendar objects

If the METHOD (specified in section 2.1.3.1.1.1) is 'REPLY' or 'COUNTER', then this property SHOULD be imported as PidLidAttendeeCriticalChange (section ).<137>

If the METHOD is not 'REPLY' or 'COUNTER', then this property MUST be imported as PidLidOwnerCriticalChange ([MS-OXPROPS] section ).

Exporting from Calendar objects

If the METHOD (specified in section 2.1.3.1.1.1) is 'REPLY' or 'COUNTER', then PidLidAttendeeCriticalChange MUST be exported as DTSTAMP.

If the METHOD is not 'REPLY' or 'COUNTER', then PidLidOwnerCriticalChange MUST be exported as DTSTAMP. If PidLidOwnerCriticalChange is undefined, the current system time SHOULD be used.

#### 2.1.3.1.1.20.9.1 Parameter: TZID

Article02/14/2019

RFC Reference: section 4.2.19

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In conjunction with a matching VTIMEZONE, specifies the time zone of a Date-Time property provided in local time.

Refer to [RFC2445] section 4.2.19 for additional details on the TZID parameter.

### 2.1.3.1.1.20.10 Property: DTSTART

Article02/14/2019

RFC Reference: section 4.8.2.4

Number of Instances Allowed: 1

Format: Date-Time ([RFC2445] section 4.3.5), Date ([RFC2445] section 4.3.4)

Brief Description: The start time of an appointment. If the item is a counter proposal, this is the proposed start time of the meeting.

Importing to Calendar objects

If the METHOD property of the VCALENDAR component is set to 'COUNTER', then this property SHOULD<138> be imported as PidLidAppointmentProposedStartWhole (section ).

If the METHOD property of the VCALENDAR component is not set to 'COUNTER' or if either X-MS-OLK-ORIGINALEND or X-MS-OLK-ORIGINALSTART is not specified, then this property SHOULD<139> be imported as PidLidAppointmentStartWhole ([MSOXPROPS] section ), and PidLidAppointmentDuration SHOULD<140> be set to the number of minutes between DTSTART and DTEND.

If DTSTART and DTEND are both specified in floating time, and if both occur at midnight of their respective days, then the appointment SHOULD<141> be imported as an allday appointment: PidLidAppointmentSubType MUST be set to 0x00000001. Note that this logic SHOULD<142> also be triggered by X-MICROSOFT-CDO-ALLDAYEVENT (section 2.1.3.1.1.20.28) and X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT (section

2.1.3.1.1.20.41).

If the DTEND and DURATION properties are not specified in the VEVENT, the value of

DTSTART MAY<143> be used to derive the end time based on the format of the DTSTART property based on the following rules.

If the format of the DTSTART property is a Date-Time, the end time is treated as being equal to the value of DTSTART, and is imported as specified in section

2.1.3.1.1.20.8.

If the format of the DTSTART property is a Date, the end time is treated as being equal to the value of DTSTART + 1 day, and is imported as specified in section

2.1.3.1.1.20.8.

Exporting from Calendar objects

If the METHOD property of the VCALENDAR component is set to 'COUNTER', then

PidLidAppointmentProposedStartWhole SHOULD<144> be exported as a new DTSTART property. For other values of METHOD, the PidLidAppointmentStartWhole of a Calendar object SHOULD<145> be exported as a DTSTART property.

If this is an all-day appointment, then this property SHOULD<146> be exported in floating time with the Date format.

If this is a recurring non-all-day appointment, then this property MUST be specified as a local time with a TZID parameter.

Non-recurring non-all-day appointments SHOULD<147> be specified as a local time with a TZID parameter.

#### 2.1.3.1.1.20.10.1 Parameter: TZID

Article02/14/2019

RFC Reference: section 4.2.19

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In conjunction with a matching VTIMEZONE, specifies the time zone of a Date-Time property provided in local time.

Importing to Calendar objects

If this appointment is recurring, and if there is a TZID parameter, then

PidLidTimeZoneStruct MUST be imported from the VTIMEZONE referenced by the TZID parameter, PidLidTimeZoneDescription MUST be imported from the TZID parameter, and PidLidAppointmentTimeZoneDefinitionRecur SHOULD<148> be imported from the VTIMEZONE referenced by the TZID parameter.

Furthermore, PidLidAppointmentTimeZoneDefinitionStartDisplay SHOULD<149> be imported from the VTIMEZONE referenced by the TZID parameter.

Refer to [RFC2445] section 4.2.19 for additional details on the TZID parameter.

Exporting from Calendar objects

If this is a recurring non-all-day appointment, then the DTSTART property MUST be specified as a local time. It MUST be accompanied by a TZID parameter referencing the VTIMEZONE described by PidLidAppointmentTimeZoneDefinitionRecur<150> or the combination of PidLidTimeZoneDescription and PidLidTimeZoneStruct.

If this is a non-recurring non-all-day appointment and if

PidLidAppointmentTimeZoneDefinitionStartDisplay is set, then the DTSTART property SHOULD<151> be specified as a local time. It MUST be accompanied by a TZID parameter referencing the VTIMEZONE described by

PidLidAppointmentTimeZoneDefinitionStartDisplay.

#### 2.1.3.1.1.20.10.2 Parameter: VALUE

Article02/14/2019

RFC Reference: section 4.2.20

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the format of this property.

Importing to Calendar objects

This parameter SHOULD<152> be ignored since a parser can determine whether a property is in the Date format ([RFC2445] section 4.3.4) or Date-Time format ([RFC2445] section 4.3.5) without an explicit declaration in the VALUE parameter.

Exporting from Calendar objects

If the DTSTART property is specified in the Date format ([RFC2445] section 4.3.4), the VALUE parameter MUST be exported as 'DATE'. If the DTSTART property is specified in the Date-Time format ([RFC2445] section 4.3.4), the VALUE parameter SHOULD be omitted, but MAY be exported as 'DATE-TIME'.

### 2.1.3.1.1.20.11 Property: DESCRIPTION

Article02/14/2019

RFC Reference: section 4.8.1.5

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the plain-text body of an appointment.

Importing to and Exporting from Calendar objects

If the METHOD property of the VCALENDAR component is set to 'REPLY' or 'COUNTER', this property SHOULD<153> be ignored. For other values of METHOD, this property MUST be mapped directly to PidTagBody.

Also see the documentation for COMMENT in section 2.1.3.1.1.20.5.

#### 2.1.3.1.1.20.11.1 Parameter: LANGUAGE

Article10/13/2020

RFC Reference: section 4.2.10

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the language of the property.

Importing to Calendar objects

This parameter SHOULD<154> be interpreted as a language tag as specified in  and stored in PidTagMessageLocaleId (section  as the corresponding language code identifier, as specified in

Exporting from Calendar objects

This parameter SHOULD NOT be exported (see section 2.1.3.1.1.20.24.1).

### 2.1.3.1.1.20.12 Property: DURATION

Article02/14/2019

RFC Reference: section 4.8.2.5

Number of Instances Allowed: 0, 1

Format: Duration ([RFC2445] section 4.3.6)

Brief Description: Specifies the duration of an appointment.

Importing to Calendar objects

If only one of DTSTART and DTEND is present, the DURATION property SHOULD<155> be used to compute the missing property.

Exporting from Calendar objects

This parameter SHOULD NOT be exported.

### 2.1.3.1.1.20.13 Property: EXDATE

Article02/14/2019

RFC Reference: section 4.8.5.1

Number of Instances Allowed: 0+

Format: Date-Time ([RFC2445] section 4.3.5), Date ([RFC2445] section 4.3.4)

Brief Description: Specifies the original start time of instances of the recurring appointment which have been deleted.

Importing to Calendar objects

If this property is specified, an RRULE MUST also be specified in the same VEVENT.

All valid EXDATEs SHOULD<156> be gathered into the DeletedInstanceDates field of the RecurrencePattern structure embedded within the AppointmentRecurrencePattern structure (section ) in the PidLidAppointmentRecur property ([MS-OXOCAL] section ) after the following validation:

All EXDATEs SHOULD<157> be converted to the time zone specified by PidLidTimeZoneStruct.

The time information MUST be stripped off (all entries MUST fall on midnight).

All duplicate entries MUST be removed.

All entries that do not have a date matching the start date of an instance in the recurrence pattern MUST be removed.

The DeletedInstanceDates field of the RecurrencePattern structure MUST be sorted chronologically with the earliest dates at the start.

Note that additional EXDATEs could be derived from the RECURRENCE-IDs of other VEVENTs (see section 2.1.3.1.1.20.20).

Exporting from Calendar objects

The EXDATE property MUST NOT be exported for non-recurring appointments or exceptions of recurring appointments.

In certain cases, an X-MICROSOFT-EXDATE SHOULD<158> be exported in place of an EXDATE. See section 2.1.3.1.1.20.39.

If there are entries in the DeletedInstanceDates field, the date-times of each day specified by the DeletedInstanceDates field SHOULD<159> be added with the time specified by the StartTimeOffset field of the RecurrencePattern structure and exported in a multi-valued EXDATE property. However, exceptions exported as a separate VEVENT with a RECURRENCE-ID (see section 2.1.3.1.1.20.20) SHOULD NOT also be exported as an EXDATE.

If the recurrence is an all-day recurrence, the EXDATEs MUST be specified in the Date format.

#### 2.1.3.1.1.20.13.1 Parameter: TZID

Article02/14/2019

RFC Reference: section 4.2.19

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In conjunction with a matching VTIMEZONE, specifies the time zone of a Date-Time property provided in local time.

Refer to [RFC2445] section 4.2.19 for additional details on the TZID parameter.

#### 2.1.3.1.1.20.13.2 Parameter: VALUE

Article02/14/2019

RFC Reference: section 4.2.20

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the format of this property.

Importing to Calendar objects

This parameter SHOULD<160> be ignored since a parser can determine whether a property is in the Date format ([RFC2445] section 4.3.4) or Date-Time format ([RFC2445] section 4.3.5) without an explicit declaration in the VALUE parameter.

Exporting from Calendar objects

If the EXDATE property is specified in the Date format ([RFC2445] section 4.3.4), the

VALUE parameter MUST be exported as 'DATE'. If the EXDATE property is specified in the Date-Time format ([RFC2445] section 4.3.5), the VALUE parameter SHOULD be omitted, but MAY be exported as 'DATE-TIME'.

### 2.1.3.1.1.20.14 Property: LAST-MODIFIED

Article • 03/18/2025

RFC Reference: section 4.8.7.3

Number of Instances Allowed: 0, 1

Format: Date-Time ([RFC2445] section 4.3.5)

Brief Description: The last modification time of an appointment.

Importing to Calendar object

This property SHOULD be ignored.<161>

Exporting from Calendar objects

The PidTagLastModificationTime (section  of a Calendar object SHOULD<162> be exported as a LAST-MODIFIED property, specified in UTC.

### 2.1.3.1.1.20.15 Property: LOCATION

Article08/17/2021

RFC Reference: section 4.8.1.7

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the location of an appointment.

Importing to Calendar objects

This property SHOULD<163> be stripped of all carriage returns (Unicode character U+000D) and line feeds (Unicode character U+000A), and SHOULD<164> be truncated to a length of 255 WCHARs if its length exceeds 255 WCHARs. The truncation SHOULD

Exporting from Calendar objects

PidLidLocation MUST be exported as a LOCATION property.

#### 2.1.3.1.1.20.15.1 Parameter: ALTREP

Article02/14/2019

RFC Reference: section 4.2.1

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies an alternate text representation of the property value.

Importing to Calendar objects

This parameter MAY<166> be imported to the PidNameLocationUrl (section 2.1.3.4.3) property.

Exporting from Calendar objects

This parameter MAY<167> be exported from the PidNameLocationUrl property.

#### 2.1.3.1.1.20.15.2 Parameter: LANGUAGE

Article02/14/2019

RFC Reference: section 4.2.10

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the language of the property.

Importing to Calendar objects

This parameter SHOULD<168> be interpreted as a language tag as specified in  and stored in PidTagMessageLocaleId as the corresponding language code identifier, as specified in .

Exporting from Calendar objects

This parameter SHOULD NOT be exported. See section 2.1.3.1.1.20.24.1.

### 2.1.3.1.1.20.16 Property: ORGANIZER

Article10/13/2020

RFC Reference: section 4.8.4.3

Number of Instances Allowed: 0, 1

Format: Calendar User Address ([RFC2445] section 4.3.3) Brief Description: The organizer of a meeting.

Importing to Calendar objects

This property SHOULD<169> be parsed as a valid mailto URI as specified in . The resulting SMTP address SHOULD be resolved against the address parameter. The Address Book object MUST be added to the recipient table of the Calendar object with properties specified in the following table.

Exporting from Calendar objects

If the 0x00000001 flag of PidLidAppointmentStateFlags is 0, then an ORGANIZER property MUST NOT be exported.

The row in the recipient table of the Calendar object that satisfies the constraints in the following table SHOULD<173> be exported as an ORGANIZER property. The value of the property MUST be a mailto URI as specified in [RFC2368] with the SMTP address of the recipient from the address book, as specified in [MS-OXOABK]. If the recipient does not have an SMTP address, then the value of the property SHOULD<174> be set to 'invalid:nomail'.

#### 2.1.3.1.1.20.16.1 Parameter: CN

Article02/14/2019

RFC Reference: section 4.2.2

Number of Instances Allowed: 0,1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: The display name of the organizer.

Importing to Calendar objects See section 2.1.3.1.1.20.16.

Exporting from Calendar objects

This parameter SHOULD be exported from the PidTagDisplayName from the Address Book object (falling back on the PidTagDisplayName from the recipient table, if necessary).

### 2.1.3.1.1.20.17 Property: PRIORITY

Article10/13/2020

RFC Reference: section 4.8.1.9

Number of Instances Allowed: 0, 1

Format: Integer ([RFC2445] section 4.3.8)

Brief Description: Specifies the importance of an appointment.

Importing to Calendar objects

If PidTagImportance ( section ) cannot be imported from X-

MICROSOFT-CDO-IMPORTANCE (section 2.1.3.1.1.20.32) or X-MICROSOFTMSNCALENDAR-IMPORTANCE (section 2.1.3.1.1.20.43), then this property MUST be imported into PidTagImportance as specified by the following table.

Exporting from Calendar objects

PidTagImportance MUST be exported as the PRIORITY property as specified by the following table.

### 2.1.3.1.1.20.18 Property: RDATE

Article10/13/2020

RFC Reference: section 4.8.5.3

Number of Instances Allowed: 0+

Format: Date-Time ([RFC2445] section 4.3.5), Date ([RFC2445] section 4.3.4), Period of Time ([RFC2445] section 4.3.9)

Brief Description: Specifies the start time of additional instances of the recurring appointment which have been created by the organizer.

Importing to Calendar objects

If this property is specified, an RRULE MUST also be specified in the same VEVENT.

RDATEs in Period of Time format SHOULD be ignored. All valid RDATEs SHOULD<175> be gathered into the ModifiedInstanceDates field of the RecurrencePattern structure (section ) embedded within the AppointmentRecurrencePattern structure ([MS-OXOCAL] section ) in the PidLidAppointmentRecur property ([MS-OXOCAL] section ), after the following validation:

All RDATEs MUST be converted to the time zone specified by PidLidTimeZoneStruct.

The time-of-day information MUST be stripped off (all entries MUST fall on midnight).

All duplicate entries MUST be removed.

Each RDATE MUST be pairable with an EXDATE to represent a moved instance of a recurring appointment. The moved instance obeys the following rules:

An instance MUST NOT be moved before the previous instance or after the next instance.

An instance MUST NOT be moved such that the intersection of its span with the span of any other instance of the appointment has a non-zero duration.

An instance MUST NOT be moved such that its start time falls on the same calendar day as that of another instance.

The ModifiedInstanceDates field in the RecurrencePattern structure MUST be sorted chronologically with the earliest dates at the start.

In addition, all valid RDATEs SHOULD<176> be stored in the ExceptionInfo field of the

AppointmentRecurrencePattern structure. The contents of each ExceptionInfo block MUST be set as specified in the following table.

Note that additional RDATEs could be derived from the DTSTARTs of other VEVENTs. See section 2.1.3.1.1.20.20. For exceptions generated by RECURRENCE-IDs, fields in the ExceptionInfo structure MUST be set according to the following table.

The following table specifies the valid values for the OverrideFlags field of the ExceptionInfo structure.

Exporting from Calendar objects

The RDATE property MUST NOT be exported for non-recurring appointments or exceptions of recurring appointments.

If there are entries in the ModifiedInstanceDates field in the RecurrencePattern structure embedded within the AppointmentRecurrencePattern structure, the datetimes of all instances of the recurrence pattern falling on the days specified by the ModifiedInstanceDates field in the RecurrencePattern structure SHOULD<177> be exported in an RDATE, but exceptions exported as a separate VEVENT with a

RECURRENCE-ID (see section 2.1.3.1.1.20.20) MUST NOT also be exported as an RDATE.

If the exception is an all-day appointment, the RDATE MUST be specified in the Date format.

#### 2.1.3.1.1.20.18.1 Parameter: TZID

Article02/14/2019

RFC Reference: section 4.2.19

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In conjunction with a matching VTIMEZONE, specifies the time zone of a Date-Time property provided in local time.

Refer to [RFC2445] section 4.2.19 for additional details on the TZID parameter.

#### 2.1.3.1.1.20.18.2 Parameter: VALUE

Article02/14/2019

RFC Reference: section 4.2.20

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the format of this property.

Importing to Calendar objects

This parameter SHOULD<178> be ignored since a parser can determine whether a property is in the Date format ([RFC2445] section 4.3.4) or Date-Time format ([RFC2445] section 4.3.5) without an explicit declaration in the VALUE parameter.

Exporting from Calendar objects

If the RDATE property is specified in the Date format ([RFC2445] section 4.3.4), the

VALUE parameter MUST be exported as 'DATE'. If the RDATE property is specified in the Date-Time format ([RFC2445] section 4.3.5), the VALUE parameter SHOULD be omitted, but MAY be exported as 'DATE-TIME'.

### 2.1.3.1.1.20.19 Property: RRULE

Article02/14/2019

RFC Reference: section 4.8.5.4

Number of Instances Allowed: 0, 1

Format: Recurrence rule ([RFC2445] section 4.3.10)

Brief Description: Specifies the recurrence pattern of a recurring appointment.

Importing to and Exporting from Calendar objects

Section 2.1.3.2.2 specifies how the RRULE property is imported and exported.

### 2.1.3.1.1.20.20 Property: RECURRENCE-ID

Article10/13/2020

RFC Reference: section 4.8.4.4

Number of Instances Allowed: 0, 1

Format: Date-Time ([RFC2445] section 4.3.5), Date ([RFC2445] section 4.3.4)

Brief Description: The original starting time of a moved exception of a recurring appointment.

Importing to Calendar objects

This property MUST be imported into PidLidExceptionReplaceTime, in UTC.

In addition, if the VCALENDAR contains a recurring VEVENT with the same UID, but no RECURRENCE-ID, this entire VEVENT SHOULD<179> be treated as an exception of the recurring VEVENT. In particular:

Instead of creating a new Calendar object in the Folder object for this VEVENT, a new Attachment object in the Recurring Calendar object SHOULD<180> be created (with properties specified in the following table), and

PidTagAttachDataObject ( section ) SHOULD<181> be opened as a Calendar object and used to import this VEVENT.

The PidTagMessageClass of this Calendar object SHOULD<182> be overwritten to 'IPM.OLE.CLASS.{00061055-0000-0000-C000-000000000046}'.

The recurring VEVENT SHOULD<183> treat this VEVENT's RECURRENCE-ID as an EXDATE, and this VEVENT's DTSTART as an RDATE. See section 2.1.3.1.1.20.18 for the effect of this exception on PidLidAppointmentRecur.

Exporting from Calendar objects

If PidLidExceptionReplaceTime is set, then it MUST be exported as a RECURRENCE-ID.

Otherwise, if an InstanceDate can be parsed from the 17th, 18th, 19th, and 20th bytes of

PidLidGlobalObjectId ([MS-OXPROPS] section  as specified in section

2.1.3.1.1.20.26, then that date combined with the time in PidLidStartRecurrenceTime

([MS-OXPROPS] section  in the time zone specified by PidLidTimeZoneStruct MUST be exported as a RECURRENCE-ID.

In addition, exceptions to recurring appointments SHOULD<184> be exported as a separate VEVENTs with a RECURRENCE-ID under either of the conditions below. Exceptions that do not fit either of these conditions MAY instead be exported as an RDATE (see section 2.1.3.1.1.20.18).

Exceptions stored as an Attachment object with PidTagAttachMethod set to

0x00000005 and with the bit denoted by 0x00000002 set to 1 in PidTagAttachmentFlags.

Exceptions which do anything other than, or in addition to, moving the start time of an instance without changing the duration.

The RECURRENCE-ID of new VEVENTs MUST be exported from the OriginalStartDate field of the corresponding ExceptionInfo block. Furthermore, the new VEVENTs MUST export the same UID as the recurring VEVENT. The remaining properties MUST be exported from the Calendar object embedded in PidTagAttachDataObject of the Attachment object. If no Attachment object exists for this exception, then the ExceptionInfo's fields MUST be exported as properties of the new VEVENT as specified in the following table.

If RECURRENCE-ID is exported (as specified above) and the recurring parent is not allday, RECURRENCE-ID MUST be specified local to the time zone specified in PidLidTimeZoneStruct.

If RECURRENCE-ID is exported (as specified above) and the recurring parent is all-day, then the RECURRENCE-ID MUST be specified in the Date format ([RFC2445] section

4.3.4).

#### 2.1.3.1.1.20.20.1 Parameter: TZID

Article02/14/2019

RFC Reference: section 4.2.19

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In conjunction with a matching VTIMEZONE, specifies the time zone of a Date-Time property provided in local time.

Refer to [RFC2445] section 4.2.19 for additional details on the TZID parameter.

#### 2.1.3.1.1.20.20.2 Parameter: VALUE

Article02/14/2019

RFC Reference: section 4.2.20

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the format of this property.

Importing to Calendar objects

This parameter SHOULD<185> be ignored since a parser can determine whether a property is in the Date format ([RFC2445] section 4.3.4) or Date-Time format ([RFC2445] section 4.3.5) without an explicit declaration in the VALUE parameter.

Exporting from Calendar objects

If the RECURRENCE-ID property is specified in the Date format ([RFC2445] section 4.3.4), the VALUE parameter MUST be exported as 'DATE'. If the RECURRENCE-ID property is specified in the Date-Time format ([RFC2445] section 4.3.5), the VALUE parameter SHOULD be omitted, but MAY be exported as 'DATE-TIME'.

### 2.1.3.1.1.20.21 Property: RESOURCES

Article02/14/2019

RFC Reference: section 4.8.1.10

Number of Instances Allowed: 0+

Format: Text ([RFC2445] section 4.3.11)

Brief Description: A resource (such as rooms or equipment) for a meeting.

Importing to Calendar objects

All instances of the RESOURCES property SHOULD<186> be parsed as a commadelimited list of strings into a string array. For each string in the array:

All semicolons (Unicode character U+003B) MUST be filtered out.

All adjacent sequences of whitespace<187> MUST be compressed to a single space (Unicode character U+0020).

All whitespace<188> at the beginning and end of the string MUST be filtered out.

Zero-length strings MUST be ignored.

All remaining strings in the array SHOULD<189> be added to a list delimited by "; " (Unicode character U+003B followed by U+0020) in PidLidNonSendableBcc.

Exporting from Calendar objects

The semicolon-delimited entries in PidLidNonSendableBcc SHOULD<190> be exported as a comma-delimited list in a RESOURCES property.

### 2.1.3.1.1.20.22 Property: SEQUENCE

Article02/14/2019

RFC Reference: section 4.8.7.4

Number of Instances Allowed: 0, 1

Format: Integer ([RFC2445] section 4.3.8)

Brief Description: Specifies the revision sequence number of the meeting request.

Importing to Calendar objects

If PidLidAppointmentSequence  section  cannot be imported from X-MICROSOFT-CDO-APPT-SEQUENCE (section 2.1.3.1.1.20.29), then this property MUST be imported into PidLidAppointmentSequence. If no SEQUENCE property exists, PidLidAppointmentSequence SHOULD<191> be left unset.

Exporting from Calendar objects

PidLidAppointmentSequence MUST be exported as the SEQUENCE property. If PidLidAppointmentSequence is not set, the SEQUENCE property MUST be exported as

0.

### 2.1.3.1.1.20.23 Property: STATUS

Article10/13/2020

RFC Reference: section 4.8.1.11

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the confirmation level of the appointment.

Importing to Calendar objects

If PidLidBusyStatus cannot be imported from TRANSP (section 2.1.3.1.1.20.25), X-

MICROSOFT-CDO-BUSYSTATUS (section 2.1.3.1.1.20.31), or X-MICROSOFT-

MSNCALENDAR-BUSYSTATUS (section 2.1.3.1.1.20.42), this property SHOULD<192> be imported into PidLidBusyStatus as specified in the following table.

Exporting from Calendar objects

This property SHOULD NOT be exported.

### 2.1.3.1.1.20.24 Property: SUMMARY

Article02/14/2019

RFC Reference: section 4.8.1.12

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the subject of an appointment.

Importing to Calendar objects

This property SHOULD<193> be stripped of all carriage returns (Unicode character U+000D) and line feeds (Unicode character U+000A), and SHOULD<194> be truncated to a length of 255 WCHARs if its length exceeds 255 WCHARs. The truncation SHOULD NOT<195> split surrogate pairs. This property MUST be stored in PidTagSubject. If this property could not be imported, PidTagSubject SHOULD<196> be set to the zerolength string.

Exporting from Calendar objects

PidTagSubject MUST be exported as a SUMMARY property. If PidTagSubject is not set, then the zero-length string SHOULD<197> be exported as a SUMMARY property.

#### 2.1.3.1.1.20.24.1 Parameter: LANGUAGE

Article02/14/2019

RFC Reference: section 4.2.10

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the language of the property.

Importing to Calendar objects

This parameter SHOULD<198> be parsed as a language tag (as specified in ) and stored in PidTagMessageLocaleId as the corresponding language code identifier.

Exporting from Calendar objects

PidTagMessageLocaleId SHOULD<199> be converted from an [MS-LCID] language code identifier to an [RFC1766] language tag and exported as a LANGUAGE parameter.

### 2.1.3.1.1.20.25 Property: TRANSP

Article10/13/2020

RFC Reference: section 4.8.2.7

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies whether or not this appointment is intended to be visible in availability searches.

Importing to Calendar objects

If PidLidBusyStatus cannot be imported from X-MICROSOFT-CDO-BUSYSTATUS (section 2.1.3.1.1.20.31) or X-MICROSOFT-MSNCALENDAR-BUSYSTATUS (section 2.1.3.1.1.20.42), this property SHOULD<200> be imported into PidLidBusyStatus as specified in the following table.

Exporting from Calendar objects

This property SHOULD<201> be exported from PidLidBusyStatus as specified in the following table.

### 2.1.3.1.1.20.26 Property: UID

Article08/17/2021

RFC Reference: section 4.8.4.7

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Provides a globally unique identifier for the appointment.

Importing to Calendar objects

There are two supported forms of textual representation of the UID property. The Augmented Backus-Naur Form (ABNF) syntax, as specified in , for this value is shown in the following example.

To be of type EncodedGlobalId, the value of the UID property MUST satisfy the following constraints:

Every character MUST be a HEXDIG.

The length of the string MUST be eighty-two (82) characters or more.

The length of the string MUST be evenly divisible by 2.

The first thirty-two characters MUST match (case insensitive)<203> "040000008200E00074C5B7101A82E008".

Otherwise, the UID property is of type ThirdPartyGlobalId.

If the UID is of type EncodedGlobalId, then the data MUST be decoded to its binary representation (every two HEXDIGs compose one byte).

A temporary variable EffectiveInstanceDate is defined as follows:

If the UID is of type EncodedGlobalId and if the InstanceDate portion of the UID is a valid date in the range of January 1st, 1601 to December 31st, 4500 (inclusive), then the EffectiveInstanceDate is the ThirdPartyGlobalId portion of the UID.

If the UID is of type EncodedGlobalId but the ThirdPartyGlobalId portion of the

UID is not a valid date in the range of January 1st, 1601 to December 31st, 4500 (inclusive), then the EffectiveInstanceDate is the date from the RECURRENCE-ID property (in its local time zone). In the case where RECURRENCE-ID property is not present, the EffectiveInstanceDate is zero (Year = Month = Day = 0).

If the UID is of type ThirdPartyGlobalId, then the EffectiveInstanceDate is the date from the RECURRENCE-ID property (in its local time zone). In the case where RECURRENCE-ID property is not present, the EffectiveInstanceDate is zero (Year = Month = Day = 0).

If the UID is of type EncodedGlobalId, it MUST be imported into PidLidGlobalObjectId as specified below. The PidLidGlobalObjectId structure is specified in section .

The Byte Array ID field MUST be set to: 0x04, 0x00, 0x00, 0x00, 0x82, 0x00, 0xE0, 0x00, 0x74, 0xC5, 0xB7, 0x10, 0x1A, 0x82, 0xE0, 0x08.

The YH field MUST be set to the high byte of the EffectiveInstanceDate's year.

The YL field MUST be set to the low byte of the EffectiveInstanceDate's year.

The M field MUST be set to the value of the EffectiveInstanceDate's month.

The D field MUST be set to the value of the EffectiveInstanceDate's day.

The Creation Time field MUST be set to the CreationDateTime value.

The X field MUST be set to the Padding value.

The Size field MUST be set to the DataSize value.

The Data field MUST be set to the binary value of GlobalIdData.

If the UID is of type EncodedGlobalId, it MUST also be imported into

PidLidCleanGlobalObjectId ( section  as specified below. The

PidLidCleanGlobalObjectId structure is specified in [MS-OXOCAL] section

The Byte Array ID field MUST be set to: 0x04, 0x00, 0x00, 0x00, 0x82, 0x00, 0xE0, 0x00, 0x74, 0xC5, 0xB7, 0x10, 0x1A, 0x82, 0xE0, 0x08.

The YH field MUST be set to 0x00.

The YL field MUST be set to 0x00.

The M field MUST be set to 0x00.

The D field MUST be set to 0x00.

The Creation Time field MUST be set to the CreationDateTime value.

The X field MUST be set to the Padding value.

The Size field MUST be set to the DataSize value.

The Data field MUST be set to the binary value of GlobalIdData.

If the UID is of type ThirdPartyGlobalId, it MUST be imported into PidLidGlobalObjectId as specified below.

The Byte Array ID field MUST be set to: 0x04, 0x00, 0x00, 0x00, 0x82, 0x00, 0xE0, 0x00, 0x74, 0xC5, 0xB7, 0x10, 0x1A, 0x82, 0xE0, 0x08.

The YH field MUST be set to the high byte of the EffectiveInstanceDate's year.

The YL field MUST be set to the low byte of the EffectiveInstanceDate's year.

The M field MUST be set to the value of the EffectiveInstanceDate's month.

The D field MUST be set to the value of the EffectiveInstanceDate's day.

The Creation Time field MUST be set to 0x0000000000000000.

The X field MUST be set to 0x0000000000000000.

The Size field MUST be set to the number of OCTETS in ThirdPartyGlobalId (UTF-8 encoded length) + 0x0000000C.

The Data field MUST be set to the following bytes: 0x76, 0x43, 0x61, 0x6C, 0x2D,

0x55, 0x69, 0x64, 0x01, 0x00, 0x00, 0x00, followed by the value of ThirdPartyGlobalId (encoded in UTF-8).

If the UID is of type ThirdPartyGlobalId, it MUST also be imported into PidLidCleanGlobalObjectId as specified below.

The Byte Array ID field MUST be set to: 0x04, 0x00, 0x00, 0x00, 0x82, 0x00, 0xE0, 0x00, 0x74, 0xC5, 0xB7, 0x10, 0x1A, 0x82, 0xE0, 0x08.

The YH field MUST be set to 0x00.

The YL field MUST be set to 0x00.

The M field MUST be set to 0x00.

The D field MUST be set to 0x00.

The Creation Time field MUST be set to 0x0000000000000000.

The X field MUST be set to 0x0000000000000000.

The Size field MUST be set to the number of OCTETS in ThirdPartyGlobalId (UTF-8 encoded length) + 0x0000000C.

The Data field MUST be set to the following bytes: 0x76, 0x43, 0x61, 0x6C, 0x2D,

0x55, 0x69, 0x64, 0x01, 0x00, 0x00, 0x00, followed by the value of ThirdPartyGlobalId (encoded in UTF-8).

Exporting from Calendar objects

If the Data field of PidLidGlobalObjectId begins with the following 12 bytes: 0x76, 0x43, 0x61, 0x6C, 0x2D, 0x55, 0x69, 0x64, 0x01, 0x00, 0x00, 0x00, the remainder of the Data field (starting at the 13th byte) MUST be treated as a UTF-8 encoded string and exported directly as the UID property.

Otherwise, a modified copy of PidLidGlobalObjectId, with the YH, YL, M, and D fields set to 0x00, MUST be encoded as a hexadecimal string, and exported as the UID property.

### 2.1.3.1.1.20.27 Property: X-ALT-DESC

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0+

Format: Text (section 4.3.11)

Brief Description: Provides an alternate format for the DESCRIPTION property (an HTML body).

Importing to Calendar objects

If the FMTTYPE parameter is 'text/HTML', then the HTML SHOULD<204> be converted to encapsulated RTF as specified in and stored in PidTagRtfCompressed, as specified in .

If the FMTTYPE parameter is absent or undocumented, then the X-ALT-DESC property SHOULD be ignored.

Exporting from Calendar objects

PidTagRtfCompressed SHOULD<205> be converted to HTML and exported as an XALT-DESC property with a FMTTYPE parameter of 'text/HTML'.

#### 2.1.3.1.1.20.27.1 Parameter: FMTTYPE

Article02/14/2019

RFC Reference: section 4.2.8

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the text format of the X-ALT-DESC property.

Importing to and Exporting from Calendar objects

See section 2.1.3.1.1.20.27.

# CDO-ALLDAYEVENT

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Boolean (section 4.3.2)

Brief Description: Specifies whether an appointment is intended to be treated as all-day.

Importing to Calendar objects

If this property is set to TRUE and if DTSTART and DTEND are both specified as local times falling at midnight in their respective<206> time zones, then this appointment

SHOULD<207> be imported as an all-day appointment. Specifically,

PidLidAppointmentSubType SHOULD<208> be set to 0x00000001 and

PidLidAppointmentStartWhole and PidLidAppointmentEndWhole SHOULD<209> be set to fall on midnight of the current system time zone (in UTC).

Exporting from Calendar objects

This property SHOULD NOT<210> be exported. Section 2.1.3.1.1.20.10 specifies how to correctly export all-day events.

# CDO-APPT-SEQUENCE

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0,1

Format: Integer ( section 4.3.8)

Brief Description: Specifies the sequence number of the meeting request.

Importing to Calendar objects

This property SHOULD<211> be imported into PidLidAppointmentSequence.

Exporting from Calendar objects

This property SHOULD NOT<212> be exported. Section 2.1.3.1.1.20.22 specifies how to correctly export PidLidAppointmentSequence using the SEQUENCE property.

# CDO-ATTENDEE-CRITICAL-CHANGE

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Date-Time (section 4.3.5)

Brief Description: Specifies the time at which the attendee accepted, tentatively accepted, or declined the meeting request.

Importing to Calendar objects

This property MAY<213> be imported as PidLidAttendeeCriticalChange.

Exporting from Calendar objects

PidLidAttendeeCriticalChange MAY<214> be exported as X-MICROSOFT-CDOATTENDEE-CRITICAL-CHANGE.

# CDO-BUSYSTATUS

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Specifies the BUSY status of an appointment.

Importing to and Exporting from Calendar objects

This property SHOULD<215> be mapped into PidLidBusyStatus as specified by the following table.

# CDO-IMPORTANCE

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Integer ( section 4.3.8)

Brief Description: Specifies the importance of an appointment.

Importing to Calendar objects

This property SHOULD be imported into PidTagImportance as specified by the following table.

Exporting from Calendar objects

This property SHOULD be exported as specified in the preceding table.

# CDO-INSTTYPE

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Integer ( section 4.3.8)

Brief Description: Indicates whether the VEVENT represents a non-recurring appointment, a recurring appointment, or an exception to a recurring appointment.

Importing to Calendar objects

This property SHOULD be ignored.

Exporting from Calendar objects

This property SHOULD NOT<216> be exported. The instance type of a VEVENT can be correctly determined based on the existence of the RRULE and RECURRENCE-ID properties.

# CDO-INTENDEDSTATUS

Article08/17/2021

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Specifies the busy status that the meeting organizer intends the attendee's copy of the meeting to have.

Importing to Calendar objects

BUSYSTATUS as specified in section 2.1.3.1.1.20.31.

If the METHOD property is REQUEST and an X-MICROSOFT-CDO-INTENDEDSTATUS property is present, the value of the PidLidBusyStatus property ( section

MAY<218> be set to 0x00000001.

If the METHOD property is REQUEST and an X-MICROSOFT-CDO-INTENDEDSTATUS property is absent, then PidLidIntendedBusyStatus SHOULD<219> copy the value of

PidLidBusyStatus, defaulting to 0x00000002 if PidLidBusyStatus was not set, and PidLidBusyStatus SHOULD<220> be set to 0x00000001.

Exporting from Calendar objects

If the METHOD property is REQUEST, PidLidIntendedBusyStatus SHOULD<221> be exported as X-MICROSOFT-CDO-INTENDEDSTATUS using the same export mapping as X-MICROSOFT-CDO-BUSYSTATUS specified in section 2.1.3.1.1.20.31.

# CDO-OWNERAPPTID

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Integer ( section 4.3.8)

Brief Description: Provides an identifier for the appointment which is unique in the scope of the organizer's primary calendar.

Importing to and Exporting from Calendar objects

This property SHOULD<222> be directly imported to and exported from PidTagOwnerAppointmentId (section .

# CDO-OWNER-CRITICAL-CHANGE

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Date-Time (section 4.3.5)

Brief Description: Specifies the time at which the organizer requested, updated, or cancelled the meeting.

Importing to Calendar objects

When present, this property MAY<223> be imported as PidLidOwnerCriticalChange.

Exporting from Calendar objects

PidLidOwnerCriticalChange MAY<224> be exported as X-MICROSOFT-CDO-OWNERCRITICAL-CHANGE.

# CDO-REPLYTIME

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Date-Time (section 4.3.5)

Brief Description: Specifies the time in which the attendee responded to a meeting request.

Importing to Calendar objects

This property MAY<225> be imported as PidLidAppointmentReplyTime.

Exporting from Calendar objects

PidLidAppointmentReplyTime MAY<226> be exported as X-MICROSOFT-CDOREPLYTIME.

# DISALLOW-COUNTER

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Boolean (section 4.3.2)

Brief Description: Specifies whether or not the organizer is willing to receive counterproposals.

Importing to and Exporting from Calendar objects

This property SHOULD<227> be directly imported to and exported from PidLidAppointmentNotAllowPropose  section .

# EXDATE

Article08/17/2021

RFC Reference: N/A

Number of Instances Allowed: 0+

Format: Date-Time (section 4.3.5), Date ([RFC2445] section 4.3.4)

Brief Description: Specifies the original start time of instances of the recurring appointment which have been deleted.

Importing to Calendar objects

If this property is specified, an X-MICROSOFT-RRULE MUST also be specified in the same VEVENT.

This property SHOULD<228> be imported in the same way that the EXDATE property is imported. See section 2.1.3.1.1.20.13.

Exporting from Calendar objects

The X-MICROSOFT-EXDATE property MUST NOT be exported for non-recurring appointments or exceptions of recurring appointments.

If the CalendarType field of the RecurrencePattern field of the

AppointmentRecurrencePattern structure ( section ) in the

PidLidAppointmentRecur property ([MS-OXOCAL] section  is non-zero or if the PatternType field is 0x000A or 0x000B, this property SHOULD<229> be exported in place of the EXDATE property. If exported, the value of this property MUST be exactly what the value of the EXDATE property would have been (see section 2.1.3.1.1.20.13).

## 2.1.3.1.1.20.39.1 Parameter: VALUE

Article02/14/2019

RFC Reference: section 4.2.20

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the format of this property.

Importing to Calendar objects

This parameter SHOULD be ignored.

Exporting from Calendar objects

This parameter MUST be exported as 'DATE-TIME'.

# ISDRAFT

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Boolean (section 4.3.2)

Brief Description: Specifies whether an appointment is a draft.

Importing to Calendar objects

For iCalendar files with a METHOD of REQUEST, REPLY, CANCEL, or COUNTER, PidLidFInvited ( section ) MUST be set to TRUE regardless of the value of X-MICROSOFT-ISDRAFT.

For iCalendar files with a METHOD of PUBLISH, PidLidFInvited SHOULD<230> be set to TRUE if the VEVENT is a meeting and X-MICROSOFT-ISDRAFT is not set to TRUE.

Otherwise, PidLidFInvited SHOULD be set to FALSE.

Exporting from Calendar objects

For iCalendar files with a METHOD of PUBLISH, if the organizer of the meeting is the user and if PidLidFInvited is not TRUE, then X-MICROSOFT-ISDRAFT SHOULD<231> be exported as TRUE.

For all other cases, X-MICROSOFT-ISDRAFT MUST NOT be exported.

# RRULE

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Recurrence rule ( section 4.3.10)

Brief Description: Specifies the recurrence pattern of a recurring appointment.

Importing to and Exporting from Calendar objects

Section 2.1.3.2.2 specifies how the X-MICROSOFT-RRULE property is imported and exported.

If this property is specified, an X-MICROSOFT-CALSCALE MUST also be specified in the same VEVENT.

## 2.1.3.1.1.20.45.1 Parameter: VALUE

Article04/16/2024

RFC Reference: section 4.2.20

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the format of this property.

Importing to Calendar objects

This parameter SHOULD be ignored.

Exporting from Calendar objects

This parameter MUST be exported as 'RECUR'.

2.1.3.1.1.20.45.2 Parameter: X-MICROSOFT-

# ISLEAPMONTH

Article • 05/20/2025

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Boolean (section 4.3.2)

Brief Description: Specifies whether the month specified in a yearly non-Gregorian recurrence is a leap month of that calendar.

Importing to Calendar objects

This parameter SHOULD be ignored. The month of a yearly recurrence is determined from DTSTART.

Exporting from Calendar objects

If the recurrence is a Yearly (section 2.1.3.2.2.5) or Yearly Nth (section 2.1.3.2.2.6), this property SHOULD<236> be exported as a Boolean ([RFC2445] section 4.3.2) indicating whether or not the month of the recurrence is a leap month.

# ALLOWEXTERNCHECK

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Boolean (section 4.3.2)

Brief Description: Specifies whether attendees not directly invited by the organizer can connect to the conferencing instance.

Importing to and Exporting from Calendar objects

This property SHOULD<237> be directly imported to and exported from PidLidAllowExternalCheck (section ).

# APPTLASTSEQUENCE

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Integer ( section 4.3.8)

Brief Description: Specifies the last-known maximum sequence number of a meeting.

Importing to and Exporting from Calendar objects

This property SHOULD<238> be directly imported to and exported from PidLidAppointmentLastSequence (section .

# APPTSEQTIME

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 1

Format: Date-Time (section 4.3.5), Date ([RFC2445] section 4.3.4) Brief Description: The creation time of the iCalendar.

Importing to Calendar objects

This property SHOULD<239> be imported (in UTC) to

PidLidAppointmentSequenceTime  section .

Exporting from Calendar objects

PidLidAppointmentSequenceTime SHOULD<240> be exported as this property (in UTC).

## 2.1.3.1.1.20.48.1 Parameter: TZID

Article02/14/2019

RFC Reference: section 4.2.19

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: In conjunction with a matching VTIMEZONE, specifies the time zone of a Date-Time property provided in local time.

Refer to [RFC2445] section 4.2.19 for additional details on the TZID parameter.

# AUTOFILLLOCATION

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Boolean (section 4.3.2)

Brief Description: Specifies whether the location is being automatically populated with recipients of type RESOURCE.

Importing to and Exporting from Calendar objects

This property SHOULD<241> be directly imported to and exported from PidLidAutoFillLocation section ).

# AUTOSTARTCHECK

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Boolean (section 4.3.2)

Brief Description: Specifies whether or not to automatically start the conferencing application when a reminder for the meeting fires.

Importing to and Exporting from Calendar objects

This property SHOULD<242> be directly imported to and exported from PidLidAutoStartCheck (section .

# COLLABORATEDOC

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Specifies the path to the conferencing collaboration document.

Importing to and Exporting from Calendar objects

This property SHOULD<243> be directly imported to and exported from PidLidCollaborateDoc  section .

# CONFCHECK

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Boolean (section 4.3.2)

Brief Description: Specifies whether or not conferencing is enabled on this appointment.

Importing to and Exporting from Calendar objects

This property SHOULD<244> be directly imported to and exported from PidLidConferencingCheck (section ).

# CONFTYPE

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Integer ( section 4.3.8)

Brief Description: Specifies the type of conferencing that is enabled on the appointment.

Importing to and Exporting from Calendar objects

This property SHOULD<245> be directly imported to and exported from PidLidConferencingType  section .

# DIRECTORY

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Specifies the path to the conferencing server.

Importing to and Exporting from Calendar objects

This property SHOULD<246>

PidLidDirectory  section .

# MWSURL

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Specifies the URL of the Meeting Workspace.

Importing to and Exporting from Calendar objects

This property SHOULD<247> be directly imported to and exported from PidLidMeetingWorkspaceUrl (section .

# NETSHOWURL

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Specifies the URL of the NetShow conference.

Importing to and Exporting from Calendar objects

This property SHOULD<248>

PidLidNetShowUrl (section .

# ONLINEPASSWORD

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Specifies the password to the conferencing instance.

Importing to and Exporting from Calendar objects

This property SHOULD<249>

PidLidOnlinePassword (section .

# ORGALIAS

Article10/13/2020

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Text (section 4.3.11)

Brief Description: Specifies the e-mail address of the conferencing instance's organizer.

Importing to and Exporting from Calendar objects

This property SHOULD<250>

PidLidOrganizerAlias (section .

# ORIGINALEND

Article04/16/2024

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Date-Time (section 4.3.5), Date ([RFC2445] section 4.3.4)

Brief Description: Specifies the original end time of a meeting on a counter proposal.

Importing to and Exporting from Calendar objects

If the METHOD property of the VCALENDAR component is set to 'COUNTER', this property SHOULD<251> be directly mapped to PidLidAppointmentEndWhole, and PidLidAppointmentDuration SHOULD<252> be set to the number of minutes between X-MS-OLK-ORIGINALSTART and X-MS-OLK-ORIGINALEND.

For other values of METHOD, X-MS-OLK-ORIGINALEND MUST be ignored and MUST NOT be exported.

# ORIGINALSTART

Article02/14/2019

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: Date-Time (section 4.3.5), Date ([RFC2445] section 4.3.4)

Brief Description: Specifies the original start time of a meeting on a counter proposal.

Importing to and Exporting from Calendar objects

If the METHOD property of the VCALENDAR component is set to 'COUNTER', this property SHOULD<253> be directly mapped to PidLidAppointmentStartWhole, and PidLidAppointmentDuration SHOULD<254> be set to the number of minutes between X-MS-OLK-ORIGINALSTART and X-MS-OLK-ORIGINALEND.

For other values of METHOD, X-MS-OLK-ORIGINALSTART MUST be ignored and MUST NOT be exported.

# SENDER

Article08/17/2021

RFC Reference: N/A

Number of Instances Allowed: 0, 1

Format: URI ( section 4.3.13)

Brief Description: The delegate sending the meeting on behalf of the organizer.

Importing to Calendar objects

This property SHOULD<255> be parsed as a valid mailto URI, as specified in . The resulting SMTP address SHOULD<256> be resolved against the address book, as specified in. If no match was found, a one-off EntryID ( section ) SHOULD<257> be created using the SMTP address and the CN parameter. If resolved successfully, the Address Book object SHOULD<258> be imported into PidTagSenderAddressType  section , PidTagSenderEmailAddress ([MS-OXPROPS] section ), PidTagSenderEntryId

([MS-OXPROPS] section ), and PidTagSenderName ([MS-OXPROPS] section

.

Exporting from Calendar objects

If the 0x00000001 flag of PidLidAppointmentStateFlags is 0, then an X-MS-OLKSENDER property MUST NOT be exported. Also, if PidTagSenderEntryId refers to the same Address Book object as the organizer, then the X-MS-OLK-SENDER property SHOULD NOT be exported.

The value of this property SHOULD<259> be a mailto URI, as specified in [RFC2368], with the SMTP address of the Address Book object, as specified in [MS-OXOABK], referenced by PidTagSenderEntryId. If the Address Book object does not have an SMTP address, then the value of the property SHOULD<260> be set to 'invalid:nomail'.

## 2.1.3.1.1.20.61.1 Parameter: CN

Article02/14/2019

RFC Reference: section 4.2.2

Number of Instances Allowed: 0,1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: The display name of the delegate sending the meeting on behalf of the organizer.

Importing to Calendar objects See section 2.1.3.1.1.20.61.

Exporting from Calendar objects

This parameter SHOULD<261> be exported from the PidTagDisplayName from the Address Book object (falling back on the PidTagSenderName from the Calendar object, if necessary).

## 2.1.3.1.1.20.62 Component: VALARM

Article10/13/2020

RFC Reference: section 4.6.6

Number of Instances Allowed: 0, 1

Brief Description: Specifies a reminder for an appointment.

Importing to Calendar objects

If there is a VALARM component with a TRIGGER property specified as a Duration ([RFC2445] section 4.3.6) or a Date-Time ([RFC2445] section 4.3.5), then it MUST be parsed according to the following table.

Exporting from Calendar objects

If PidLidReminderSet is TRUE, then a VALARM component MUST be exported with the properties specified in the following table.

### 2.1.3.1.1.20.62.1 Property: TRIGGER

Article02/14/2019

RFC Reference: section 4.8.6.3

Number of Instances Allowed: 1

Format: Duration ([RFC2445] section 4.3.6), Date-Time ([RFC2445] section 4.3.5)

Brief Description: Specifies the signal time of the reminder as an interval, in minutes, before the beginning of an instance of the appointment.

Importing to and Exporting from Calendar objects

See 2.1.3.1.1.20.62.

### 2.1.3.1.1.20.62.2 Property: ACTION

Article02/14/2019

RFC Reference: section 4.8.6.1

Number of Instances Allowed: 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the action to take when the reminder is signaled.

Importing to Calendar objects

This property SHOULD be ignored on import.

Exporting from Calendar objects

See 2.1.3.1.1.20.62.

### 2.1.3.1.1.20.62.3 Property: DESCRIPTION

Article02/14/2019

RFC Reference: section 4.8.1.5

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Provides a plain-text description for the reminder.

Importing to Calendar objects

This property SHOULD be ignored on import.

Exporting from Calendar objects

See 2.1.3.1.1.20.62.

## 2.1.3.2 Additional Information on Recurrences

Article02/14/2019

Additional information that is necessary to specify a mapping from iCalendar RRULEs to PidLidAppointmentRecur can be found below.

### 2.1.3.2.1 iCalendar Recurrence Syntax

Article04/16/2024

An iCalendar recurrence data type is a semicolon-delimited list of recurrence parts. The ordering of these recurrence parts does not matter, but a single iCalendar recurrence MUST NOT contain more than one instance of the same recurrence part.

#### 2.1.3.2.1.1 Recurrence Part: FREQ

Article10/13/2020

RFC Reference: section 4.3.10

Number of Instances Allowed: 1

Format: Text ([RFC2445] section 4.3.11)

Brief Description: Specifies the frequency of the recurrence.

The FREQ recurrence part MUST be set to one of the values defined in the following table.

#### 2.1.3.2.1.2 Recurrence Part: INTERVAL

Article10/13/2020

RFC Reference: section 4.3.10

Number of Instances Allowed: 0, 1

Format: Integer ([RFC2445] section 4.3.8)

Brief Description: Specifies a multiplier for the period of a recurrence.

The INTERVAL recurrence part MUST be within the bounds defined in the following table. If an INTERVAL is omitted, the recurrence MUST be parsed as though the INTERVAL were 1.

#### 2.1.3.2.1.3 Recurrence Part: BYMINUTE

Article02/14/2019

RFC Reference: section 4.3.10

Number of Instances Allowed: 0, 1

Format: Integer ([RFC2445] section 4.3.8)

Brief Description: Specifies the minute(s) on which a recurrence occurs.

The BYMINUTE recurrence part MUST be an integer between 0 and 59 (inclusive). Furthermore, the BYMINUTE recurrence part MUST NOT specify more than one value. If no BYMINUTE is specified, the minute from the DTSTART property MUST be used.

#### 2.1.3.2.1.4 Recurrence Part: BYHOUR

Article02/14/2019

RFC Reference: section 4.3.10

Number of Instances Allowed: 0, 1

Format: Integer ([RFC2445] section 4.3.8)

Brief Description: Specifies the hour(s) on which a recurrence occurs.

The BYHOUR recurrence part MUST be an integer between 0 and 23 (inclusive). Furthermore, the BYHOUR recurrence part MUST NOT specify more than one value. If no BYHOUR is specified, the hour from the DTSTART property MUST be used.

2.1.3.2.1.5 Recurrence Part:

# BYMONTHDAY

Article02/14/2019

RFC Reference: section 4.3.10

Number of Instances Allowed: Dependent on the recurrence template (section 2.1.3.2.2

Format: Integer ([RFC2445] section 4.3.8)

Brief Description: Specifies the day(s) of the month on which a recurrence occurs.

The BYMONTHDAY recurrence part MUST be -1, or an integer between 1 and 31 (inclusive). Furthermore, the BYMONTHDAY recurrence part MUST NOT specify more than one value. If no BYMONTHDAY is specified, the day of month from the DTSTART property MUST be used.

## 2.1.3.2.1.6 Recurrence Part: BYDAY

Article10/13/2020

RFC Reference: section 4.3.10

Number of Instances Allowed: Dependent on the recurrence template (section 2.1.3.2.2)

Format: Text ([RFC2445] section 4.3.8)

Brief Description: Specifies the day(s) of the week on which a recurrence occurs.

The BYDAY recurrence part MUST be a comma-delimited list of elements consisting of an optional week number followed by a mandatory 2-character code for the day of week. A BYDAY recurrence part with no week number will be termed week independent.

The following table specifies the possible values for the mandatory character code for the day of the week.

The following table specifies the possible values for the optional week number.

## 2.1.3.2.1.7 Recurrence Part: BYMONTH

Article02/14/2019

RFC Reference: section 4.3.10

Number of Instances Allowed: Dependent on the recurrence template (section 2.1.3.2.2)

Format: Integer ([RFC2445] section 4.3.8)

Brief Description: Specifies the month(s) on which a recurrence occurs.

The BYMONTH recurrence part MUST be an integer between 1 and 12 (inclusive). Furthermore, the BYMONTH recurrence part MUST NOT specify more than one value. If no BYMONTH is specified, the month from the DTSTART property MUST be used.

## 2.1.3.2.1.8 Recurrence Part: BYSETPOS

Article10/13/2020

RFC Reference: section 4.3.10

Number of Instances Allowed: Dependent on the recurrence template (section 2.1.3.2.2)

Format: Integer ([RFC2445] section 4.3.8)

Brief Description: Specifies the instances of a multi-BYDAY appointment to use each INTERVAL (see section 2.1.3.2.2.4 and 2.1.3.2.2.6).

The BYSETPOS recurrence part MUST be -1 or an integer between 1 and 4 (inclusive), as specified in the following table. Furthermore, the BYSETPOS recurrence part MUST NOT specify more than one value.

## 2.1.3.2.1.9 Recurrence Part: WKST

Article02/14/2019

RFC Reference: section 4.3.10

Number of Instances Allowed: 0, 1

Format: Text ([RFC2445] section 4.3.8)

Brief Description: Specifies the day of week on which a week is considered to start.

The WKST recurrence part MUST one of the day of week character codes specified in section 2.1.3.2.1.6. If no WKST recurrence part is specified, 'SU' MUST be used.

## 2.1.3.2.1.10 Recurrence Part: UNTIL

Article02/14/2019

RFC Reference: section 4.3.10

Number of Instances Allowed: 0, 1

Format: Date-Time ([RFC2445] section 4.3.5)

Brief Description: Specifies the time of the last instance of a recurring appointment (inclusive).

The UNTIL recurrence part MUST be a Date-Time occurring after the DTSTART property. The UNTIL recurrence part MUST NOT be specified in conjunction with the COUNT recurrence part. If neither an UNTIL nor a COUNT is specified, the recurrence MUST be treated as infinitely recurring. If the last instance of a recurring appointment would occur on or after January 1, 4501 in the time zone specified by PidLidTimeZoneStruct, the recurrence SHOULD<267> be treated as infinitely recurring.

## 2.1.3.2.1.11 Recurrence Part: COUNT

Article02/14/2019

RFC Reference: section 4.3.10

Number of Instances Allowed: 0, 1

Format: Integer ([RFC2445] section 4.3.8)

Brief Description: Specifies the number of instances in a recurring appointment.

The COUNT recurrence part MUST be an Integer between 1 and 999 (inclusive). The COUNT recurrence part MUST NOT be specified in conjunction with the UNTIL recurrence part. If neither an UNTIL nor a COUNT is specified, the recurrence MUST be treated as infinitely recurring. If the last instance of a recurring appointment would occur on or after January 1, 4501, the recurrence SHOULD<268> be treated as infinitely recurring.

## 2.1.3.2.2 Recurrence Templates

Article08/17/2021

The RRULE and X-MICROSOFT-RRULE properties MUST NOT be exported for nonrecurring appointments or exceptions of recurring appointments.

Although the syntax permits a wide variety of recurrences, only RRULE properties and X-

MICROSOFT-RRULE properties fitting the templates enumerated in this section

section ).

Implementations SHOULD gracefully fail to map any recurrences that do not fit the templates enumerated in this section.

Once a recurrence has been successfully mapped into the

AppointmentRecurrencePattern structure, implementations SHOULD<270> also set the PidLidClipStart property ([MS-OXOCAL] section  to the value of the StartDate field of the AppointmentRecurrencePattern structure and set the PidLidClipEnd property ([MS-OXOCAL] section ) to the value of the EndDate field of the AppointmentRecurrencePattern structure.

The following sections express the templates in ABNF notation, as specified in . The following code shows common rules used in the templates.

### 2.1.3.2.2.1 Template: Daily Recurrences

Article08/17/2021

ABNF Description

daily-template= "FREQ=DAILY" [common-parts]

Template Examples Every day:

FREQ=DAILY

Every day at 3:30 P.M.:

FREQ=DAILY;BYMINUTE=30;BYHOUR=15

Every 3 days:

FREQ=DAILY;INTERVAL=3

Every 3 days at 3:30 P.M.:

FREQ=DAILY;INTERVAL=3;BYMINUTE=30;BYHOUR=15

Every 3 days at 3:30 P.M. for 30 instances:

FREQ=DAILY;INTERVAL=3;BYMINUTE=30;BYHOUR=15;COUNT=30

Importing to Calendar objects

An RRULE or X-MICROSOFT-RRULE matching this template SHOULD<271> be imported into PidLidAppointmentRecur as specified in the following table. A VEVENT MUST NOT specify both an RRULE and an X-MICROSOFT-RRULE.

The following table specifies how to map WKST values to FirstDOW values.

Exporting From Calendar objects

The AppointmentRecurrencePattern structure ([MS-OXOCAL] section ) in the PidLidAppointmentRecur property ([MS-OXOCAL] section  SHOULD<272> be exported as the property specified in the following table. If a case matches more than one row, the first matching row applies.

The exported property MUST be assigned the value generated by the recurrence template specified in the following table.

If PidLidAppointmentRecur is being exported with the Daily Recurrence template, it MUST contain the recurrence parts specified in the following table.

### 2.1.3.2.2.2 Template: Weekly Recurrences

Article10/13/2020

ABNF Description

weekly-template= "FREQ=WEEKLY" [byday-part] [common-parts]

Template Examples

Every Monday and Tuesday:

FREQ=WEEKLY;BYDAY=MO,TU

Every Monday and Tuesday at 3:30 P.M:

FREQ=WEEKLY;BYDAY=MO,TU;BYMINUTE=30;BYHOUR=15

The Monday and Tuesday of every two weeks, for 7 occurrences:

FREQ=WEEKLY;BYDAY=MO,TU;INTERVAL=2;COUNT=7

The Sunday and Monday of every two weeks, as interpreted by someone who considers a week to start on Monday (common in European Union countries). This is different in that, after a Sunday instance, there will be a seven-day gap before the next instance on a Monday:

FREQ=WEEKLY;BYDAY=SU,MO;INTERVAL=2;WKST=MO

Importing to Calendar objects

An RRULE or X-MICROSOFT-RRULE matching this template SHOULD<278> be imported into PidLidAppointmentRecur as specified in the following table. A VEVENT MUST NOT specify both an RRULE and an X-MICROSOFT-RRULE. The BYDAY recurrence part MUST be week independent.

The following table specifies how to map BYDAY values to a PatternTypeSpecific.Week.Sa-Su bitmask.

Exporting from Calendar objects

The AppointmentRecurrencePattern structure ([MS-OXOCAL] section ) in the PidLidAppointmentRecur property ([MS-OXOCAL] section  SHOULD<279> be exported as the property specified by the table of recurrence properties in section 2.1.3.2.2.1. The exported property MUST be assigned the value generated by the Recurrence template specified by the table of recurrence templates specified in section

2.1.3.2.2.1.

If PidLidAppointmentRecur is being exported with the Weekly Recurrence template, then it MUST contain the recurrence parts specified in the following table.

### 2.1.3.2.2.3 Template: Monthly Recurrences

Article10/13/2020

ABNF Description

monthly-template= "FREQ=MONTHLY" [bymonthday-part] [common-parts]

Template Examples

The last day of every month:

FREQ=MONTHLY;BYMONTHDAY=-1

The 10th day of every month at 3:30 P.M:

FREQ=MONTHLY;BYMONTHDAY=10;BYMINUTE=30;BYHOUR=15

The 15th day of every 3 months, for 7 occurrences:

FREQ=MONTHLY;BYMONTHDAY=15;INTERVAL=3;COUNT=7

Importing to Calendar objects

An RRULE or X-MICROSOFT-RRULE matching this template SHOULD<283> be imported into PidLidAppointmentRecur as specified in the following table. A VEVENT MUST NOT specify both an RRULE and an X-MICROSOFT-RRULE.

Exporting from Calendar objects

The AppointmentRecurrencePattern structure ([MS-OXOCAL] section ) in the PidLidAppointmentRecur property ([MS-OXOCAL] section  SHOULD<286> be exported as the property specified by the table of recurrence properties in section

2.1.3.2.2.1. The exported property MUST be assigned the value generated by the Recurrence template specified by the table of Recurrence templates specified in section

2.1.3.2.2.1.

If PidLidAppointmentRecur is being exported with the Monthly Recurrence Template, it MUST contain the recurrence parts specified in the following table.

### 2.1.3.2.2.4 Template: Monthly Nth Recurrences

Article10/13/2020

ABNF Description

monthlynth-template= "FREQ=MONTHLY" monthlynth-args  monthlynth-args= byday-nth-part bysetpos-part [common-parts]

Template Examples

The 3rd Sunday of every month:

FREQ=MONTHLY;BYDAY=SU;BYSETPOS=3

The last weekday of every month at 3:30 P.M.:

FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1;BYMINUTE=30;BYHOUR=15

The first Monday of every month, for 7 occurrences:

FREQ=MONTHLY;BYDAY=MO;BYSETPOS=1;COUNT=7

Importing to Calendar objects

An RRULE or X-MICROSOFT-RRULE matching this template SHOULD<291> be imported into PidLidAppointmentRecur as specified in the following table. A VEVENT MUST NOT specify both an RRULE and an X-MICROSOFT-RRULE.

Exporting from Calendar objects

The AppointmentRecurrencePattern structure ([MS-OXOCAL] section ) in the PidLidAppointmentRecur property ([MS-OXOCAL] section  SHOULD<293> be exported as the property specified by the table of recurrence properties in section 2.1.3.2.2.1. The exported property MUST be assigned the value generated by the Recurrence template specified by the table of recurrence templates specified in section

2.1.3.2.2.1.

If PidLidAppointmentRecur is being exported with the Monthly Nth Recurrence template, then it MUST contain the recurrence parts specified in the following table.

### 2.1.3.2.2.5 Template: Yearly Recurrences

Article10/13/2020

ABNF Description

yearly-template= "FREQ=YEARLY" yearly-args

yearly-args= [bymonthday-part] [bymonth-part] [common-parts]

Template Examples

The last day of every September:

FREQ=YEARLY;BYMONTHDAY=-1;BYMONTH=9

The 10th day of every January at 3:30 P.M.:

FREQ=YEARLY;BYMONTHDAY=10;BYMONTH=1;BYMINUTE=30;BYHOUR=15

The 15th day of March, every 3 years, for 7 occurrences:

FREQ=YEARLY;BYMONTHDAY=15;BYMONTH=3;INTERVAL=3;COUNT=7

Importing to Calendar objects

An RRULE or X-MICROSOFT-RRULE matching this template SHOULD<297> be imported into PidLidAppointmentRecur as specified in the following table. A VEVENT MUST NOT specify both an RRULE and an X-MICROSOFT-RRULE.

Exporting from Calendar objects

The AppointmentRecurrencePattern structure ([MS-OXOCAL] section ) in the PidLidAppointmentRecur property ([MS-OXOCAL] section  SHOULD<300> be exported as the property specified by the table of recurrence properties in section

2.1.3.2.2.1. The exported property MUST be assigned the value generated by the Recurrence template specified by the table of Recurrence templates specified in section

2.1.3.2.2.1.

If PidLidAppointmentRecur is being exported with the Yearly Recurrence Template, then it MUST contain the recurrence parts specified in the following table.

### 2.1.3.2.2.6 Template: Yearly Nth Recurrences

Article10/13/2020

ABNF Description

yearlynth-template= "FREQ=YEARLY" yearlynth-args [common-parts]  yearlynth-args= byday-nth-part bysetpos-part bymonth-part

Template Examples

The 3rd Sunday of every June:

FREQ=YEARLY;BYDAY=SU;BYSETPOS=3;BYMONTH=6

The last weekday of every April at 3:30 P.M.:

FREQ=YEARLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1;BYMONTH=4;BYMINUTE=30;BYHOUR=1 5

The first Monday of every October, every 3 years, for 7 occurrences:

FREQ=YEARLY;BYDAY=MO;BYSETPOS=1;BYMONTH=10;INTERVAL=3;COUNT=7

Importing to Calendar objects

An RRULE or X-MICROSOFT-RRULE matching this template SHOULD<305> be imported into PidLidAppointmentRecur as specified in the following table. A VEVENT MUST NOT specify both an RRULE and an X-MICROSOFT-RRULE.

Exporting from Calendar objects

The AppointmentRecurrencePattern structure ([MS-OXOCAL] section ) in the PidLidAppointmentRecur property ([MS-OXOCAL] section  SHOULD<307> be exported as the property specified by the table of recurrence properties in section

2.1.3.2.2.1. The exported property MUST be assigned the value generated by the Recurrence template specified by the table of Recurrence templates specified in section

2.1.3.2.2.1.

If PidLidAppointmentRecur is being exported with the Yearly Nth Recurrence Template, it MUST contain the recurrence parts specified in the following table.

## 2.1.3.2.3 End-of-Month Concerns

Article02/14/2019

specifies that Monthly Recurrences (section 2.1.3.2.2.3) in which the BYMONTHDAY recurrence part is 29, 30, or 31 MUST skip over months that do not have a sufficient number of days. Conversely,  specifies that Monthly Recurrences with a PatternTypeSpecific.Month.Day of 0x0000001D, 0x0000001E, or 0x0000001F MUST occur on the last day of months that do not have a sufficient number of days.

## 2.1.3.2.4 Legacy UNTIL Concerns

Article02/14/2019

If the PRODID property (see section 2.1.3.1.1.2) indicates that a version of the MIMEDIR between 1 and 11 (inclusive) generated the iCalendar file and if the UNTIL recurrence part is specified with a trailing 'Z', it SHOULD NOT<311> be treated as a UTC Date-time. Instead, only the year, month, and day of the Date-time SHOULD<312> be retained, and the UNTIL recurrence part SHOULD<313> be interpreted as 11:59 P.M. of that day (in the time zone specified by PidLidTimeZoneStruct).

## 2.1.3.3 Additional Rules for MIME Messages

Article10/13/2020

For import scenarios where the original iCalendar data is contained in a MIME message, implementations MAY<314> set additional properties on the Calendar object, as specified in the following table.

## 2.1.3.4 Calendar Object Properties

Article02/14/2019

This algorithm specifies the following additional properties for Calendar objects.

PidLidInboundICalStream (section 2.1.3.4.1)

PidLidSingleBodyICal (section 2.1.3.4.2)

PidNameLocationUrl (section 2.1.3.4.3)

### 2.1.3.4.1 PidLidInboundICalStream

Article10/13/2020

Type: PtypBinary section )

The PidLidInboundICalStream property (section  is an optional property on Calendar objects that were converted from MIME messages. It contains the contents of the iCalendar MIME part of the original MIME message.

### 2.1.3.4.2 PidLidSingleBodyICal

Article10/13/2020

Type: PtypBoolean  section

The PidLidSingleBodyICal property ( section ) is an optional property on Calendar objects that were converted from MIME messages. A value of TRUE indicates that the original MIME message contained a single MIME part.

### 2.1.3.4.3 PidNameLocationUrl

Article10/13/2020

Type: PtypString  section

The PidNameLocationUrl property ( section ) is an optional property on Calendar objects. It contains a URL where attendees can access location information in HTML format.

# 3 Algorithm Examples

Article02/14/2019

The following subsections contain annotated iCalendar files representing several example scenarios.

## 3.1 Birthday Calendar for 2008

Article08/17/2021

In this example, Elizabeth has a non-primary calendar containing the birthdays of herself (October 12, 1975) and her closest friends: Shu (February 27, 1978) and Anne (July 7, 1982). Elizabeth sets 7-day reminders on all the birthdays so she has enough time to prepare. The following tables represent the contents of the Birthday calendar's Folder object and its three Calendar objects.

The following table shows the property on the Folder object.

The following table lists the properties on the Calendar object for Elizabeth's Birthday.

54

The following table lists the properties on the Calendar object for Shu's Birthday.

54

The following table lists the properties on the Calendar object for Anne's Birthday.

D

D

54

Elizabeth saves her calendar to share with Shu. The following shows the resulting iCalendar file.

BEGIN:VCALENDAR

PRODID:-//Microsoft Corporation//Outlook 12.0 MIMEDIR//EN

VERSION:2.0

METHOD:PUBLISH

X-CALSTART:19751012T000000

X-WR-RELCALID:{00000018-0E80-EBB5-82FB-58F695E239B2}

X-WR-CALNAME:Birthdays

BEGIN:VEVENT

CLASS:PUBLIC

CREATED:20080206T190802Z

DESCRIPTION:Happy Birthday to me!\n

DTEND;VALUE=DATE:19751013

DTSTAMP:20080206T191251Z

DTSTART;VALUE=DATE:19751012

LAST-MODIFIED:20080206T190802Z

PRIORITY:5

RRULE:FREQ=YEARLY;BYMONTHDAY=12;BYMONTH=10

SEQUENCE:0

SUMMARY;LANGUAGE=en-us:Elizabeth's Birthday

END:VALARM

END:VEVENT

END:VCALENDAR

Shu opens the iCalendar file. The following tables represent the contents of the Birthday calendar's Folder object and its three Calendar objects in Shu's message store.

The following table shows the property on the Folder object.

The following table lists the properties on the Calendar object for Elizabeth's Birthday.

0

The following table lists the properties on the Calendar object for Shu's Birthday.

A

A

The following table lists the properties on the Calendar object for Anne's Birthday.

D

D

## 3.2 Schedule for the Week of June 16, 2008

Article08/17/2021

In this example, Elizabeth's primary calendar contains her schedule for the work-week of June 16, 2008.

The following table lists the properties on the Calendar object for Elizabeth's lunch break.

54

The following table lists the properties on the Calendar object for Elizabeth's doctor appointment.

FDD

FDD

54

The following table lists the properties on the Calendar object for the Fabrikam Project pre-meeting.

1

54

The following table lists the properties on the Calendar object for the Fabrikam Project meeting.

Elizabeth saves her calendar to share with Shu. The following shows the resulting iCalendar file.

BEGIN:VCALENDAR

PRODID:-//Microsoft Corporation//Outlook 12.0 MIMEDIR//EN

VERSION:2.0

X-MICROSOFT-CDO-IMPORTANCE:2

X-MICROSOFT-DISALLOW-COUNTER:FALSE

X-MS-OLK-ALLOWEXTERNCHECK:TRUE

X-MS-OLK-APPTSEQTIME:20080206T193334Z

X-MS-OLK-AUTOFILLLOCATION:FALSE

X-MS-OLK-CONFTYPE:0

BEGIN:VALARM

TRIGGER:-PT15M

ACTION:DISPLAY

DESCRIPTION:Reminder

END:VALARM

END:VEVENT

END:VCALENDAR

Shu opens the iCalendar file. The following tables represent the contents of Shu's copy of Elizabeth's Schedule.

The following table lists the properties on the Calendar object for Elizabeth's lunch break.

D

The following table lists the properties on the Calendar object for Elizabeth's doctor appointment.

FDD

The following table lists the properties on the Calendar object for the Fabrikam Project pre-meeting.

A

0

The following table lists the properties on the Calendar object for the Fabrikam Project meeting.

0

## 3.3 Single Meeting Scenario

Article02/14/2019

This subsection describes a multi-step scenario in which an organizer, Elizabeth, sets up a meeting with an attendee, Shu, but later decides to cancel it.

### 3.3.1 Organizer's Meeting Request

Article08/17/2021

Elizabeth invites Shu to lunch at Fourth Coffee from noon to 12:30 P.M. (Pacific Time) on February 8, 2008.

The following table lists the properties on the Calendar object that Elizabeth sends.

B

B

The following shows the resulting iCalendar file.

BEGIN:VCALENDAR

PRODID:-//Microsoft Corporation//Outlook 12.0 MIMEDIR//EN

VERSION:2.0

METHOD:REQUEST

X-MS-OLK-FORCEINSPECTOROPEN:TRUE

BEGIN:VEVENT

ATTENDEE;CN=sito@contoso.com;RSVP=TRUE:mailto:sito@contoso.com

CLASS:PUBLIC

CREATED:20080208T173955Z

DESCRIPTION:When: Friday\, February 08\, 2008 12:00 PM-12:30 PM (GMT-08:00)        Pacific Time (US & Canada).\nWhere: Fourth Coffee\n\n*~*~*~*~*~*~*~*~*~*\       n\nI haven't had a raspberry scone in forever!  Want to head down to Fou       rth Coffee for lunch?\n  DTEND:20080208T203000Z

DTSTAMP:20080208T173955Z

DTSTART:20080208T200000Z

LAST-MODIFIED:20080208T173955Z

LOCATION:Fourth Coffee

ORGANIZER;CN="Elizabeth Andersen":mailto:eandersen@contoso.com

PRIORITY:5

SEQUENCE:0

SUMMARY;LANGUAGE=en-us:Lunch?

TRANSP:OPAQUE

UID:040000008200E00074C5B7101A82E0080000000010C4F838346AC801000000000000000

0100000002009EB53F098B249AD66CBE6BB3B8B99

X-ALT-DESC;FMTTYPE=text/html:<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//E       N">\n<HTML>\n<HEAD>\n<META NAME="Generator" CONTENT="MS Exchange Server ve       rsion 08.00.0681.000">\n<TITLE></TITLE>\n</HEAD>\n<BODY>\n<!-- Converted f       rom text/rtf format -->\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calib       ri">When: Friday\, February 08\, 2008 12:00 PM-12:30 PM (GMT-08:00) Pacifi       c Time (US &amp\; Canada).</FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-       us"><FONT FACE="Calibri">Where: Fourth Coffee</FONT></SPAN></P>\n\n<P DIR=       LTR><SPAN LANG="en-us"><FONT FACE="Calibri">*~*~*~*~*~*~*~*~*~*</FONT></SP       AN></P>\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calibri">I haven't        had a raspberry scone in forever!&nbsp\; Want to head down to Fourth Coffe       e for lunch?</FONT></SPAN><SPAN LANG="en-us"></SPAN></P>\n\n</BODY>\n</HTM       L>

X-MICROSOFT-CDO-BUSYSTATUS:TENTATIVE

X-MICROSOFT-CDO-IMPORTANCE:1

X-MICROSOFT-CDO-INTENDEDSTATUS:BUSY

X-MICROSOFT-DISALLOW-COUNTER:FALSE

X-MS-OLK-ALLOWEXTERNCHECK:TRUE

X-MS-OLK-AUTOSTARTCHECK:FALSE

X-MS-OLK-CONFTYPE:0

X-MS-OLK-SENDER;CN="Elizabeth Andersen":mailto:eandersen@contoso.com

BEGIN:VALARM

TRIGGER:-PT15M

ACTION:DISPLAY

DESCRIPTION:Reminder

END:VALARM

END:VEVENT

END:VCALENDAR

The following table lists the properties on the Calendar object that Shu receives.

0

### 3.3.2 Attendee's Meeting Acceptance

Article10/13/2020

Shu accepts Elizabeth's meeting request.

The following table lists the properties on the Calendar object that Shu sends.

CB

CB

The following shows the resulting iCalendar file.

The following table lists the properties on the Calendar object that Elizabeth receives.

AD

AD

### 3.3.3 Organizer's Cancellation

Article08/17/2021

Elizabeth realizes that she has a conflicting meeting, so she cancels her lunch with Shu.

The following table lists the properties on the Calendar object that Elizabeth sends.

B

B

The following shows the resulting iCalendar file.

BEGIN:VCALENDAR

PRODID:-//Microsoft Corporation//Outlook 12.0 MIMEDIR//EN

VERSION:2.0

METHOD:CANCEL

X-MS-OLK-FORCEINSPECTOROPEN:TRUE

BEGIN:VEVENT

ATTENDEE;CN=sito@contoso.com;RSVP=TRUE:mailto:sito@contoso.com

CLASS:PUBLIC

CREATED:20080208T175248Z

DESCRIPTION:When: Friday\, February 08\, 2008 12:00 PM-12:30 PM (GMT-08:00)        Pacific Time (US & Canada).\nWhere: Fourth Coffee\n\n*~*~*~*~*~*~*~*~*~*\       n\nOops!  Forgot I have a meeting today. Maybe we can try again sometime        next week.\n  DTEND:20080208T203000Z

DTSTAMP:20080208T175248Z

DTSTART:20080208T200000Z

LAST-MODIFIED:20080208T175249Z

LOCATION:Fourth Coffee

ORGANIZER;CN="Elizabeth Andersen":mailto:eandersen@contoso.com

PRIORITY:1

SEQUENCE:1

SUMMARY;LANGUAGE=en-us:Canceled: Lunch?

TRANSP:TRANSPARENT

UID:040000008200E00074C5B7101A82E0080000000010C4F838346AC801000000000000000

0100000002009EB53F098B249AD66CBE6BB3B8B99

X-ALT-DESC;FMTTYPE=text/html:<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//E       N">\n<HTML>\n<HEAD>\n<META NAME="Generator" CONTENT="MS Exchange Server ve       rsion 08.00.0681.000">\n<TITLE></TITLE>\n</HEAD>\n<BODY>\n<!-- Converted f       rom text/rtf format -->\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calib       ri">When: Friday\, February 08\, 2008 12:00 PM-12:30 PM (GMT-08:00) Pacifi       c Time (US &amp\; Canada).</FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-       us"><FONT FACE="Calibri">Where: Fourth Coffee</FONT></SPAN></P>\n\n<P DIR=       LTR><SPAN LANG="en-us"><FONT FACE="Calibri">*~*~*~*~*~*~*~*~*~*</FONT></SP

AN></P>\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calibri">Oops!&nbsp\;        Forgot I have a meeting today.&nbsp\; Maybe we can try again sometime nex       t week.</FONT></SPAN><SPAN LANG="en-us"></SPAN></P>\n\n</BODY>\n</HTML>  X-MICROSOFT-CDO-BUSYSTATUS:FREE

X-MICROSOFT-CDO-IMPORTANCE:2

X-MICROSOFT-DISALLOW-COUNTER:FALSE

X-MS-OLK-ALLOWEXTERNCHECK:TRUE

X-MS-OLK-APPTSEQTIME:20080208T174833Z

X-MS-OLK-AUTOSTARTCHECK:FALSE

X-MS-OLK-CONFTYPE:0

X-MS-OLK-SENDER;CN="Elizabeth Andersen":mailto:eandersen@contoso.com

END:VEVENT

END:VCALENDAR

The following table lists the properties on the Calendar object that Shu receives.

B

0

## 3.4 Recurring Meeting Scenario

Article02/14/2019

This subsection describes a multi-step scenario in which an organizer, Elizabeth, sets up a recurring meeting with Shu, Patrick, and Anne, but cancels an instance that coincides with the company picnic. Shortly thereafter, Elizabeth corrects a typo in the Location field.

This section also documents Shu's tentative acceptance of the meeting series.

### 3.4.1 Organizer's Meeting Request

Article08/17/2021

Elizabeth organizes a weekly status meeting for Project Northwind on Wednesdays at 2:00 P.M. with Shu, Patrick, and Anne.

The following table lists the properties on the Calendar object that Elizabeth sends.

The following code shows  the iCalendar generated to send over the wire.

BEGIN:VCALENDAR

PRODID:-//Microsoft Corporation//Outlook 12.0 MIMEDIR//EN

VERSION:2.0

METHOD:REQUEST

X-MS-OLK-FORCEINSPECTOROPEN:TRUE

BEGIN:VTIMEZONE

TZID:Pacific Time (US & Canada)

BEGIN:STANDARD

DTSTART:16011104T020000

RRULE:FREQ=YEARLY;BYDAY=1SU;BYMONTH=11

TZOFFSETFROM:-0700

TZOFFSETTO:-0800

END:STANDARD

BEGIN:DAYLIGHT

DTSTART:16010311T020000

RRULE:FREQ=YEARLY;BYDAY=2SU;BYMONTH=3

TZOFFSETFROM:-0800

TZOFFSETTO:-0700

END:DAYLIGHT

END:VTIMEZONE

BEGIN:VEVENT

ATTENDEE;CN=sito@contoso.com;RSVP=TRUE:mailto:sito@contoso.com

ATTENDEE;CN=pcook@contoso.com;RSVP=TRUE:mailto:pcook@contoso.com

ATTENDEE;CN=aweiler@contoso.com;RSVP=TRUE:mailto:aweiler@contoso.com

CLASS:PUBLIC

CREATED:20080208T213320Z

DESCRIPTION:When: Occurs every Wednesday effective 2/13/2008 from 2:00 PM t       o 2:30 PM (GMT-08:00) Pacific Time (US & Canada).\nWhere: Conference Room        123\n\n*~*~*~*~*~*~*~*~*~*\n\nHey all\,\n\nLet's meet up every Wednesday        to sync up on the status of the Fabrikam Project.\n\nThanks\,\nElizabeth\       n

DTEND;TZID="Pacific Time (US & Canada)":20080213T143000

DTSTAMP:20080208T213320Z

DTSTART;TZID="Pacific Time (US & Canada)":20080213T140000

LAST-MODIFIED:20080208T213321Z

LOCATION:Conference Room 123  ORGANIZER;CN="Elizabeth Andersen":mailto:eandersen@contoso.com

PRIORITY:5

RRULE:FREQ=WEEKLY;BYDAY=WE

SEQUENCE:0

SUMMARY;LANGUAGE=en-us:Fabrikam Project Status Meeting

TRANSP:OPAQUE

UID:040000008200E00074C5B7101A82E008000000003046642B576AC801000000000000000

010000000622C639E40D09342B747A1672730CBBA

X-ALT-DESC;FMTTYPE=text/html:<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//E       N">\n<HTML>\n<HEAD>\n<META NAME="Generator" CONTENT="MS Exchange Server ve       rsion 08.00.0681.000">\n<TITLE></TITLE>\n</HEAD>\n<BODY>\n<!-- Converted f       rom text/rtf format -->\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calib       ri">When: Occurs every Wednesday effective 2/13/2008 from 2:00 PM to 2:30        PM (GMT-08:00) Pacific Time (US &amp\; Canada).</FONT></SPAN></P>\n\n<P DI

R=LTR><SPAN LANG="en-us"><FONT FACE="Calibri">Where: Conference Room 123</

FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calibri">*~*

~*~*~*~*~*~*~*~*</FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT

FACE="Calibri">Hey all\,</FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-us       "><FONT FACE="Calibri">Let's meet up every Wednesday to sync up on the s       tatus of the Fabrikam Project.</FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG=       "en-us"><FONT FACE="Calibri">Thanks\,</FONT></SPAN></P>\n\n<P DIR=LTR><SPA       N LANG="en-us"><FONT FACE="Calibri">Elizabeth</FONT></SPAN><SPAN LANG="en-       us"></SPAN></P>\n\n</BODY>\n</HTML>

X-MICROSOFT-CDO-BUSYSTATUS:TENTATIVE

X-MICROSOFT-CDO-IMPORTANCE:1

X-MICROSOFT-CDO-INTENDEDSTATUS:BUSY

X-MICROSOFT-DISALLOW-COUNTER:FALSE

X-MS-OLK-ALLOWEXTERNCHECK:TRUE

X-MS-OLK-AUTOSTARTCHECK:FALSE

X-MS-OLK-CONFTYPE:0

X-MS-OLK-SENDER;CN="Elizabeth Andersen":mailto:eandersen@contoso.com

BEGIN:VALARM

TRIGGER:-PT15M

ACTION:DISPLAY

DESCRIPTION:Reminder

END:VALARM

END:VEVENT

END:VCALENDAR

The following table lists the properties on the Calendar object that Shu receives.

0

0

### 3.4.2 Organizer's Cancellation of an Instance

Article08/17/2021

Elizabeth cancels the May 28th instance of the status meeting because it conflicts with the company picnic.

The following table lists the properties on the Calendar object that Elizabeth sends.

123

1

The following shows the resulting iCalendar file.

BEGIN:VCALENDAR

PRODID:-//Microsoft Corporation//Outlook 12.0 MIMEDIR//EN

VERSION:2.0

METHOD:CANCEL

X-MS-OLK-FORCEINSPECTOROPEN:TRUE

BEGIN:VTIMEZONE

TZID:Pacific Standard Time

BEGIN:STANDARD

DTSTART:16011104T020000

RRULE:FREQ=YEARLY;BYDAY=1SU;BYMONTH=11

TZOFFSETFROM:-0700

TZOFFSETTO:-0800

END:STANDARD

BEGIN:DAYLIGHT

DTSTART:16010311T020000

RRULE:FREQ=YEARLY;BYDAY=2SU;BYMONTH=3

TZOFFSETFROM:-0800

TZOFFSETTO:-0700

END:DAYLIGHT

END:VTIMEZONE

BEGIN:VEVENT

ATTENDEE;CN=sito@contoso.com;RSVP=TRUE:mailto:sito@contoso.com

ATTENDEE;CN=pcook@contoso.com;RSVP=TRUE:mailto:pcook@contoso.com

ATTENDEE;CN=aweiler@contoso.com;RSVP=TRUE:mailto:aweiler@contoso.com

CLASS:PUBLIC

CREATED:20080208T213455Z

DESCRIPTION:When: Wednesday\, May 28\, 2008 2:00 PM-2:30 PM (GMT-08:00) Pac       ific Time (US & Canada).\nWhere: Conference Room 123\n\n*~*~*~*~*~*~*~*~*~       *\n\nCancelling the May 28th meeting due to a conflict with the Company Pi       cnic.\n

DTEND;TZID="Pacific Standard Time":20080528T143000

DTSTAMP:20080208T213456Z

DTSTART;TZID="Pacific Standard Time":20080528T140000

LAST-MODIFIED:20080208T213456Z

LOCATION:Conference Room 123

ORGANIZER;CN="Elizabeth Andersen":mailto:eandersen@contoso.com

PRIORITY:1

RECURRENCE-ID;TZID="Pacific Standard Time":20080528T140000

SEQUENCE:0

SUMMARY;LANGUAGE=en-us:Canceled: Fabrikam Project Status Meeting

TRANSP:TRANSPARENT

UID:040000008200E00074C5B7101A82E008000000003046642B576AC801000000000000000

010000000622C639E40D09342B747A1672730CBBA

X-ALT-DESC;FMTTYPE=text/html:<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//E       N">\n<HTML>\n<HEAD>\n<META NAME="Generator" CONTENT="MS Exchange Server ve       rsion 08.00.0681.000">\n<TITLE></TITLE>\n</HEAD>\n<BODY>\n<!-- Converted f       rom text/rtf format -->\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calib       ri">When: Wednesday\, May 28\, 2008 2:00 PM-2:30 PM (GMT-08:00) Pacific Ti       me (US &amp\; Canada).</FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-us">       <FONT FACE="Calibri">Where: Conference Room 123</FONT></SPAN></P>\n\n<P DI

R=LTR><SPAN LANG="en-us"><FONT FACE="Calibri">*~*~*~*~*~*~*~*~*~*</FONT></       SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calibri">Cancelling        the May 28</FONT></SPAN><SPAN LANG="en-us"><SUP><FONT FACE="Calibri">th</       FONT></SUP></SPAN><SPAN LANG="en-us"><FONT FACE="Calibri"> meeting due to        a conflict with the Company Picnic.</FONT></SPAN><SPAN LANG="en-us"></SPAN

></P>\n\n</BODY>\n</HTML>

X-MICROSOFT-CDO-BUSYSTATUS:FREE

X-MICROSOFT-CDO-IMPORTANCE:2

X-MICROSOFT-DISALLOW-COUNTER:FALSE

X-MS-OLK-ALLOWEXTERNCHECK:TRUE

X-MS-OLK-APPTSEQTIME:20080208T213320Z

X-MS-OLK-AUTOSTARTCHECK:FALSE

X-MS-OLK-CONFTYPE:0

X-MS-OLK-SENDER;CN="Elizabeth Andersen":mailto:eandersen@contoso.com

END:VEVENT

END:VCALENDAR

The following table lists the properties on the Calendar object that Shu receives.

123

0

### 3.4.3 Organizer's Location Change of an Instance

Article08/17/2021

Elizabeth realizes that she mistyped the Conference Room number, and sends out a meeting update.

The following table lists the properties on the Calendar object that Elizabeth sends.

The following shows the resulting iCalendar file.

BEGIN:VCALENDAR

PRODID:-//Microsoft Corporation//Outlook 12.0 MIMEDIR//EN

VERSION:2.0

METHOD:REQUEST

X-MS-OLK-FORCEINSPECTOROPEN:TRUE

BEGIN:VTIMEZONE

TZID:Pacific Time (US & Canada)

BEGIN:STANDARD

DTSTART:16011104T020000

RRULE:FREQ=YEARLY;BYDAY=1SU;BYMONTH=11

TZOFFSETFROM:-0700

TZOFFSETTO:-0800

END:STANDARD

BEGIN:DAYLIGHT

DTSTART:16010311T020000

RRULE:FREQ=YEARLY;BYDAY=2SU;BYMONTH=3

TZOFFSETFROM:-0800

TZOFFSETTO:-0700

END:DAYLIGHT

END:VTIMEZONE

BEGIN:VEVENT

ATTENDEE;CN=sito@contoso.com;RSVP=TRUE:mailto:sito@contoso.com

ATTENDEE;CN=pcook@contoso.com;RSVP=TRUE:mailto:pcook@contoso.com

ATTENDEE;CN=aweiler@contoso.com;RSVP=TRUE:mailto:aweiler@contoso.com

CLASS:PUBLIC

CREATED:20080208T213600Z

DESCRIPTION:When: Occurs every Wednesday effective 2/13/2008 from 2:00 PM t       o 2:30 PM (GMT-08:00) Pacific Time (US & Canada).\nWhere: Conference Room        1234\n\n*~*~*~*~*~*~*~*~*~*\n\n(Corrected a typo in the Conference Room nu       mber)\n\nHey all\,\n\nLet's meet up every Wednesday to sync up on the st       atus of the Fabrikam Project.\n\nThanks\,\nElizabeth\n

DTEND;TZID="Pacific Time (US & Canada)":20080213T143000

DTSTAMP:20080208T213600Z

DTSTART;TZID="Pacific Time (US & Canada)":20080213T140000

EXDATE;TZID="Pacific Time (US & Canada)":20080528T140000

LAST-MODIFIED:20080208T213600Z

LOCATION:Conference Room 1234

ORGANIZER;CN="Elizabeth Andersen":mailto:eandersen@contoso.com

PRIORITY:5

RRULE:FREQ=WEEKLY;BYDAY=WE

SEQUENCE:1

SUMMARY;LANGUAGE=en-us:Fabrikam Project Status Meeting

TRANSP:OPAQUE

UID:040000008200E00074C5B7101A82E008000000003046642B576AC801000000000000000

010000000622C639E40D09342B747A1672730CBBA

X-ALT-DESC;FMTTYPE=text/html:<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//E       N">\n<HTML>\n<HEAD>\n<META NAME="Generator" CONTENT="MS Exchange Server ve       rsion 08.00.0681.000">\n<TITLE></TITLE>\n</HEAD>\n<BODY>\n<!-- Converted f       rom text/rtf format -->\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calib       ri">When: Occurs every Wednesday effective 2/13/2008 from 2:00 PM to 2:30        PM (GMT-08:00) Pacific Time (US &amp\; Canada).</FONT></SPAN></P>\n\n<P DI

R=LTR><SPAN LANG="en-us"><FONT FACE="Calibri">Where: Conference Room 1234<

/FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calibri">*~

*~*~*~*~*~*~*~*~*</FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT

FACE="Calibri">(Corrected a typo in the Conference Room number)</FONT></S       PAN></P>\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calibri">Hey all\,</

FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calibri">Let       's meet up every Wednesday to sync up on the status of the Fabrikam Proj       ect.</FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE="Calibr       i">Thanks\,</FONT></SPAN></P>\n\n<P DIR=LTR><SPAN LANG="en-us"><FONT FACE=       "Calibri">Elizabeth</FONT></SPAN><SPAN LANG="en-us"></SPAN></P>\n\n</BODY>

\n</HTML>

X-MICROSOFT-CDO-BUSYSTATUS:TENTATIVE

X-MICROSOFT-CDO-IMPORTANCE:1

X-MICROSOFT-CDO-INTENDEDSTATUS:BUSY

X-MICROSOFT-DISALLOW-COUNTER:FALSE

X-MS-OLK-ALLOWEXTERNCHECK:TRUE

X-MS-OLK-APPTSEQTIME:20080208T213320Z

X-MS-OLK-AUTOSTARTCHECK:FALSE

X-MS-OLK-CONFTYPE:0

X-MS-OLK-SENDER;CN="Elizabeth Andersen":mailto:eandersen@contoso.com

BEGIN:VALARM

TRIGGER:-PT15M

ACTION:DISPLAY

DESCRIPTION:Reminder

END:VALARM

END:VEVENT

END:VCALENDAR

The following table lists the properties on the Calendar object that Shu receives.

0

### 3.4.4 Attendee's Tentative Acceptance of the Series

Article08/17/2021

Shu tentatively accepts the recurring meeting.

The following table lists the properties on the Calendar object that Shu sends.

9

9

The following shows the resulting iCalendar file.

The following table lists the properties on the Calendar object that Elizabeth receives.