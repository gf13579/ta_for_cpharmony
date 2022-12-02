
# Add-on for Checkpoint Harmony

The Add-on for Checkpoint Harmony runs threat hunting queries in Checkpoint Harmony in order to ingest EDR detection events ('Active Attacks' as seen in the console).

## Installation

Ensure you have an account (email/password) with access to the Check Point Infinity Portal (portal.checkpoint.com) and the ability to access the Threat Hunting tab.

Install the add-on on a search head or heavy forwarder - or any Splunk Enterprise server with HTTPS connectivity to checkpoint.com.

Configure the Check Point user account's password in the add-on's setup page.

Configure a new data input, providing:
- Query Age (Hours Ago - e.g. 2)
- Region (e.g. ap for Asia-Pacific)
- Username (email address of the Check Point user)
- Interval (e.g. 300 to query every 5 minutes)
- Sourcetype (leave as the default: `checkpoint:harmony:json`)
- index (avoid Default/main)

## Alerting

The add-on uses a time-based poll approach with no checkpointing; the scheduled query may well end up ingesting duplicate events. A future release may add functionality to maintain state, but for now just dedupe events at search time.

Similarly, limited work has been done on props to make the data prettier and more CIM compliant. The scheduled search query below is aliasing and coalescing at search time.

```
index=checkpoint_events sourcetype=checkpoint:harmony:json 
| table _time, DetectionEvent.DetectionIncidentId, DetectionEvent.DetectionIncidentSeverity, MachineName, OSVersion, UserName, DomainName, HostType, DetectionEvent.DetectionAttack*, DetectionEvent.DetectionMaliciousFileName, DetectionEvent.DetectionMaliciousPath, DetectionEvent.DetectionProtectionType*, DetectionEvent.DetectionTriggerMD5, DetectionEvent.DetectionAttackTriggerProc, DetectionEvent.DetectionMalwareFamily, DetectionEvent.DetectionFirstEPFileName, Base.ProcessName, Base.ProcessMD5, Base.ProcessPath, Base.ParentProcessName, Base.ParentProcessDir, Base.ParentProcessClassification, Base.RecordType, DetectionEvent.DetectionRemediationPolicy, DetectionEvent.DetectionProtectionName
| rename DetectionEvent.DetectionIncidentSeverity AS severity, DetectionEvent.DetectionMaliciousPath AS file_path, DetectionEvent.DetectionMaliciousFileName AS file_name, DetectionEvent.DetectionTriggerMD5 AS file_hash, DetectionEvent.DetectionTriggerMD5 AS file_hash, MachineName AS dest, UserName AS src_user, DetectionEvent.DetectionIncidentId as id, DetectionEvent.DetectionProtectionType AS category, Base.ParentProcessName as parent_process_name, Base.ParentProcessDir AS parent_process_dir
| eval parent_process = parent_process_dir + "\\" + parent_process_name  
| rename DetectionEvent.DetectionMalwareFamily AS DetectionMalwareFamily, DetectionEvent.DetectionProtectionName AS DetectionProtectionName 
| eval signature=if(DetectionMalwareFamily="",DetectionProtectionName,DetectionMalwareFamily) 
|  dedup id
| rename DetectionEvent.DetectionProtectionType as detection_protection_type 
| eval url="https://ap.portal.checkpoint.com/dashboard/endpoint/threathunting#/search" 
| eval vendor_product = "Checkpoint Harmony"
```