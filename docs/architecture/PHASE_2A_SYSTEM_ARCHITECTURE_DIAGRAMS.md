# Phase 2A: System Architecture Diagrams

## Overview

This document provides comprehensive architectural diagrams for Phase 2A optimization components, showing the integration of ConnectionManager and RequestPipeline with the existing CalendarBot WebServer infrastructure.

## 1. High-Level System Architecture

### Phase 2A Component Overview

```mermaid
graph TB
    subgraph "Phase 2A Optimization Layer"
        CM[ConnectionManager]
        RP[RequestPipeline]
        CM <--> RP
    end
    
    subgraph "Existing WebServer Infrastructure"
        WS[WebServer]
        WRH[WebRequestHandler]
        API[API Handlers]
        WS --> WRH
        WRH --> API
    end
    
    subgraph "External Resources"
        DB[(SQLite Database)]
        HTTP[External HTTP APIs]
        FS[File System]
    end
    
    subgraph "Client Layer"
        UI[Web Browser]
        REST[REST Clients]
    end
    
    UI --> WS
    REST --> WS
    WS --> CM
    WS --> RP
    RP --> CM
    CM --> DB
    CM --> HTTP
    WS --> FS
    
    classDef optimization fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef existing fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef external fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef client fill:#fff3e0,stroke:#e65100,stroke-width:2px
    
    class CM,RP optimization
    class WS,WRH,API existing
    class DB,HTTP,FS external
    class UI,REST client
```

## 2. Detailed Component Architecture

### ConnectionManager Internal Architecture

```mermaid
graph TB
    subgraph "ConnectionManager"
        CMC[ConnectionManager Core]
        HSP[HTTP Session Pool]
        DBP[Database Pool]
        ELM[Event Loop Manager]
        CHM[Connection Health Monitor]
        
        CMC --> HSP
        CMC --> DBP
        CMC --> ELM
        CMC --> CHM
        
        subgraph "HTTP Pool Components"
            TC[TCPConnector]
            CS[ClientSession]
            CP[Connection Pool]
            HSP --> TC
            HSP --> CS
            HSP --> CP
        end
        
        subgraph "Database Pool Components"
            AC[Async Connections]
            CQ[Connection Queue]
            TM[Transaction Manager]
            DBP --> AC
            DBP --> CQ
            DBP --> TM
        end
        
        subgraph "Event Loop Components"
            SEL[Shared Event Loop]
            TH[Loop Thread]
            EX[Executor]
            ELM --> SEL
            ELM --> TH
            ELM --> EX
        end
    end
    
    classDef core fill:#e3f2fd,stroke:#0277bd,stroke-width:2px
    classDef pool fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef monitor fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    
    class CMC core
    class HSP,DBP,ELM,TC,CS,CP,AC,CQ,TM,SEL,TH,EX pool
    class CHM monitor
```

### RequestPipeline Internal Architecture

```mermaid
graph TB
    subgraph "RequestPipeline"
        RPC[RequestPipeline Core]
        RC[Response Cache]
        RB[Request Batcher]
        RD[Request Deduplicator]
        CKG[Cache Key Generator]
        
        RPC --> RC
        RPC --> RB
        RPC --> RD
        RPC --> CKG
        
        subgraph "Caching Components"
            TC[TTL Cache]
            CIM[Cache Invalidation Manager]
            CWM[Cache Warming Manager]
            MEC[Memory Efficient Cache]
            RC --> TC
            RC --> CIM
            RC --> CWM
            RC --> MEC
        end
        
        subgraph "Batching Components"
            BQ[Batch Queue]
            BE[Batch Executor]
            BT[Batch Timer]
            BR[Batch Requests]
            RB --> BQ
            RB --> BE
            RB --> BT
            RB --> BR
        end
        
        subgraph "Performance Components"
            CS[Cache Stats]
            PM[Performance Metrics]
            FP[Failure Policies]
            RPC --> CS
            RPC --> PM
            RPC --> FP
        end
    end
    
    classDef core fill:#e3f2fd,stroke:#0277bd,stroke-width:2px
    classDef cache fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef batch fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef perf fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class RPC,CKG core
    class RC,TC,CIM,CWM,MEC cache
    class RB,BQ,BE,BT,BR batch
    class RD,CS,PM,FP perf
```

## 3. Request Flow Architecture

### Standard Request Processing Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant WS as WebServer
    participant WRH as WebRequestHandler
    participant RP as RequestPipeline
    participant CM as ConnectionManager
    participant DB as Database
    participant Cache as ResponseCache
    
    C->>WS: HTTP Request
    WS->>WRH: Route Request
    WRH->>RP: Process Request
    
    RP->>Cache: Check Cache
    alt Cache Hit
        Cache-->>RP: Return Cached Response
        RP-->>WRH: Cached Result
    else Cache Miss
        RP->>CM: Execute Query
        CM->>DB: Database Operation
        DB-->>CM: Query Result
        CM-->>RP: Processed Result
        RP->>Cache: Store in Cache
        RP-->>WRH: Fresh Result
    end
    
    WRH-->>WS: Response Data
    WS-->>C: HTTP Response
    
    Note over RP,CM: Phase 2A Optimization Layer
    Note over Cache: TTL: 5min, Size: 1000 items
    Note over CM: Connection Pool: 100 total, 30/host
```

### Batched Request Processing Flow

```mermaid
sequenceDiagram
    participant C1 as Client 1
    participant C2 as Client 2
    participant CN as Client N
    participant WS as WebServer
    participant RP as RequestPipeline
    participant RB as RequestBatcher
    participant CM as ConnectionManager
    participant DB as Database
    
    C1->>WS: Request A
    C2->>WS: Request B
    CN->>WS: Request N
    
    WS->>RP: Route Requests
    RP->>RB: Queue for Batching
    
    Note over RB: Accumulate similar requests<br/>Max batch size: 10<br/>Max timeout: 50ms
    
    RB->>RB: Form Batch
    RB->>CM: Execute Batch
    CM->>DB: Optimized Query
    DB-->>CM: Batch Results
    CM-->>RB: Processed Results
    
    RB-->>RP: Individual Results
    RP-->>WS: Response A
    RP-->>WS: Response B
    RP-->>WS: Response N
    
    WS-->>C1: HTTP Response A
    WS-->>C2: HTTP Response B
    WS-->>CN: HTTP Response N
```

## 4. Integration Architecture

### WebServer Integration Points

```mermaid
graph TB
    subgraph "Enhanced WebServer Architecture"
        WS[WebServer Class]
        WRH[WebRequestHandler]
        
        subgraph "Phase 2A Components"
            CM[ConnectionManager]
            RP[RequestPipeline]
        end
        
        subgraph "Existing Components"
            DM[Display Manager]
            CAM[Cache Manager]
            SS[Settings Service]
            LR[Layout Registry]
        end
        
        subgraph "New Integration Layer"
            OWH[Optimized WebRequestHandler]
            API[Enhanced API Handlers]
            CONFIG[Configuration Manager]
        end
        
        WS --> CM
        WS --> RP
        WS --> CONFIG
        WRH --> OWH
        OWH --> API
        API --> RP
        RP --> CM
        
        WS --> DM
        WS --> CAM
        WS --> SS
        WS --> LR
        
        CONFIG --> CM
        CONFIG --> RP
    end
    
    subgraph "External Integration"
        ENV[Environment Variables]
        FLAGS[Feature Flags]
        MON[Monitoring System]
    end
    
    CONFIG --> ENV
    CONFIG --> FLAGS
    CM --> MON
    RP --> MON
    
    classDef new fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef existing fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef integration fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef external fill:#fff3e0,stroke:#e65100,stroke-width:2px
    
    class CM,RP new
    class WS,WRH,DM,CAM,SS,LR existing
    class OWH,API,CONFIG integration
    class ENV,FLAGS,MON external
```

## 5. Data Flow Architecture

### Connection Pool Data Flow

```mermaid
graph TD
    subgraph "Request Sources"
        API1[API Request 1]
        API2[API Request 2]
        APIN[API Request N]
    end
    
    subgraph "Connection Management Layer"
        CPM[Connection Pool Manager]
        
        subgraph "HTTP Connection Pool"
            HC1[HTTP Connection 1]
            HC2[HTTP Connection 2]
            HCN[HTTP Connection N]
        end
        
        subgraph "Database Connection Pool"
            DC1[DB Connection 1]
            DC2[DB Connection 2]
            DCN[DB Connection N]
        end
        
        CPM --> HC1
        CPM --> HC2
        CPM --> HCN
        CPM --> DC1
        CPM --> DC2
        CPM --> DCN
    end
    
    subgraph "Resource Targets"
        EXT[External APIs]
        DB[(Database)]
        FS[File System]
    end
    
    API1 --> CPM
    API2 --> CPM
    APIN --> CPM
    
    HC1 --> EXT
    HC2 --> EXT
    HCN --> EXT
    
    DC1 --> DB
    DC2 --> DB
    DCN --> DB
    
    CPM --> FS
    
    classDef request fill:#e3f2fd,stroke:#0277bd,stroke-width:2px
    classDef pool fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef resource fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    
    class API1,API2,APIN request
    class CPM,HC1,HC2,HCN,DC1,DC2,DCN pool
    class EXT,DB,FS resource
```

### Cache and Pipeline Data Flow

```mermaid
graph TD
    subgraph "Request Processing"
        REQ[Incoming Request]
        CKG[Cache Key Generator]
        CL[Cache Lookup]
        CH[Cache Hit]
        CM[Cache Miss]
    end
    
    subgraph "Cache Layer"
        L1[L1 Cache - Memory]
        TTL[TTL Expiration]
        INV[Cache Invalidation]
        WARM[Cache Warming]
    end
    
    subgraph "Processing Layer"
        BATCH[Batch Formation]
        EXEC[Execution Engine]
        DEDUP[Deduplication]
        PROC[Data Processing]
    end
    
    subgraph "Storage Layer"
        DB[(Database)]
        EXT[External APIs]
        FS[File System]
    end
    
    REQ --> CKG
    CKG --> CL
    CL --> CH
    CL --> CM
    
    CH --> L1
    CM --> DEDUP
    DEDUP --> BATCH
    BATCH --> EXEC
    EXEC --> PROC
    
    PROC --> DB
    PROC --> EXT
    PROC --> FS
    
    PROC --> L1
    L1 --> TTL
    L1 --> INV
    WARM --> L1
    
    classDef request fill:#e3f2fd,stroke:#0277bd,stroke-width:2px
    classDef cache fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef processing fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef storage fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class REQ,CKG,CL,CH,CM request
    class L1,TTL,INV,WARM cache
    class BATCH,EXEC,DEDUP,PROC processing
    class DB,EXT,FS storage
```

## 6. Performance Architecture

### Memory Usage Distribution

```mermaid
pie title Phase 2A Memory Allocation
    "HTTP Connection Pool" : 25
    "Database Connection Pool" : 15
    "Response Cache (TTL)" : 40
    "Request Pipeline Infrastructure" : 10
    "Monitoring & Metrics" : 5
    "Configuration & Overhead" : 5
```

### Performance Monitoring Architecture

```mermaid
graph TB
    subgraph "Performance Monitoring System"
        subgraph "Connection Metrics"
            CPM[Connection Pool Metrics]
            HCM[HTTP Connection Metrics]
            DCM[Database Connection Metrics]
        end
        
        subgraph "Pipeline Metrics"
            CAM[Cache Metrics]
            BAM[Batch Metrics]
            RTM[Response Time Metrics]
        end
        
        subgraph "System Metrics"
            MEM[Memory Usage]
            CPU[CPU Utilization]
            THR[Throughput]
        end
        
        subgraph "Aggregation Layer"
            COL[Metrics Collector]
            AGG[Metrics Aggregator]
            EXP[Metrics Exporter]
        end
        
        CPM --> COL
        HCM --> COL
        DCM --> COL
        CAM --> COL
        BAM --> COL
        RTM --> COL
        MEM --> COL
        CPU --> COL
        THR --> COL
        
        COL --> AGG
        AGG --> EXP
    end
    
    subgraph "External Monitoring"
        DASH[Performance Dashboard]
        ALERT[Alert System]
        LOG[Log Aggregation]
    end
    
    EXP --> DASH
    EXP --> ALERT
    EXP --> LOG
    
    classDef metrics fill:#e3f2fd,stroke:#0277bd,stroke-width:2px
    classDef aggregation fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef external fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    
    class CPM,HCM,DCM,CAM,BAM,RTM,MEM,CPU,THR metrics
    class COL,AGG,EXP aggregation
    class DASH,ALERT,LOG external
```

## 7. Deployment Architecture

### Component Deployment View

```mermaid
graph TB
    subgraph "Pi Zero 2W Deployment Environment"
        subgraph "Python Process Space"
            subgraph "Main Thread"
                WS[WebServer]
                WRH[WebRequestHandler]
                CONFIG[Configuration]
            end
            
            subgraph "Optimization Thread Pool"
                CM[ConnectionManager]
                RP[RequestPipeline]
                EL[Event Loop Thread]
            end
            
            subgraph "Background Threads"
                CW[Cache Warming Thread]
                HM[Health Monitor Thread]
                MT[Metrics Collection Thread]
            end
        end
        
        subgraph "System Resources"
            MEM[Memory: 512MB RAM]
            CPU[CPU: ARM64 Quad Core]
            STOR[Storage: MicroSD]
            NET[Network: WiFi/Ethernet]
        end
        
        subgraph "Local Storage"
            DB[(SQLite Database)]
            CACHE[File System Cache]
            LOGS[Log Files]
        end
    end
    
    WS --> CM
    WS --> RP
    CM --> EL
    RP --> CW
    CM --> HM
    RP --> MT
    
    CM --> DB
    RP --> CACHE
    HM --> LOGS
    
    classDef process fill:#e3f2fd,stroke:#0277bd,stroke-width:2px
    classDef resource fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef storage fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    
    class WS,WRH,CONFIG,CM,RP,EL,CW,HM,MT process
    class MEM,CPU,STOR,NET resource
    class DB,CACHE,LOGS storage
```

## 8. Error Handling and Recovery Architecture

### Failure Recovery Flow

```mermaid
graph TD
    subgraph "Error Detection"
        CF[Connection Failure]
        CE[Cache Error]
        BE[Batch Error]
        ME[Memory Error]
    end
    
    subgraph "Error Handling"
        EH[Error Handler]
        EH --> FP[Failure Policy Engine]
        
        subgraph "Recovery Strategies"
            CR[Connection Recovery]
            FR[Fallback Router]
            GD[Graceful Degradation]
            EM[Emergency Mode]
        end
        
        FP --> CR
        FP --> FR
        FP --> GD
        FP --> EM
    end
    
    subgraph "Recovery Actions"
        RC[Reconnect]
        CB[Circuit Breaker]
        LB[Load Balancing]
        CS[Cache Swap]
    end
    
    CF --> EH
    CE --> EH
    BE --> EH
    ME --> EH
    
    CR --> RC
    FR --> CB
    GD --> LB
    EM --> CS
    
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef handler fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef recovery fill:#e3f2fd,stroke:#0277bd,stroke-width:2px
    
    class CF,CE,BE,ME error
    class EH,FP,CR,FR,GD,EM handler
    class RC,CB,LB,CS recovery
```

## 9. Security Architecture

### Security Boundary Definition

```mermaid
graph TB
    subgraph "External Boundary"
        INT[Internet]
        NET[Network Layer]
    end
    
    subgraph "Application Boundary"
        subgraph "Web Layer Security"
            TLS[TLS Termination]
            AUTH[Authentication]
            RATE[Rate Limiting]
        end
        
        subgraph "Optimization Layer Security"
            VLD[Input Validation]
            SAN[Data Sanitization]
            ACC[Access Control]
        end
        
        subgraph "Data Layer Security"
            ENC[Data Encryption]
            ACL[Database ACL]
            AUD[Audit Logging]
        end
    end
    
    subgraph "System Boundary"
        FS[File System]
        PROC[Process Isolation]
        MEM[Memory Protection]
    end
    
    INT --> NET
    NET --> TLS
    TLS --> AUTH
    AUTH --> RATE
    RATE --> VLD
    VLD --> SAN
    SAN --> ACC
    ACC --> ENC
    ENC --> ACL
    ACL --> AUD
    AUD --> FS
    FS --> PROC
    PROC --> MEM
    
    classDef external fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef web fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef optimization fill:#e3f2fd,stroke:#0277bd,stroke-width:2px
    classDef data fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef system fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    
    class INT,NET external
    class TLS,AUTH,RATE web
    class VLD,SAN,ACC optimization
    class ENC,ACL,AUD data
    class FS,PROC,MEM system
```

## 10. Configuration Architecture

### Configuration Management Hierarchy

```mermaid
graph TD
    subgraph "Configuration Sources"
        DEF[Default Values]
        ENV[Environment Variables]
        FILE[Config Files]
        CLI[Command Line Args]
        RT[Runtime Settings]
    end
    
    subgraph "Configuration Management"
        CM[Configuration Manager]
        VP[Value Processor]
        VAL[Validator]
        OV[Override Engine]
    end
    
    subgraph "Component Configuration"
        CC[Connection Config]
        PC[Pipeline Config]
        MC[Monitoring Config]
        SC[Security Config]
    end
    
    subgraph "Feature Flags"
        FF[Feature Flag Engine]
        
        subgraph "Phase 2A Flags"
            CPF[Connection Pool Flag]
            RPF[Request Pipeline Flag]
            BF[Batching Flag]
            CF[Caching Flag]
        end
    end
    
    DEF --> CM
    ENV --> CM
    FILE --> CM
    CLI --> CM
    RT --> CM
    
    CM --> VP
    VP --> VAL
    VAL --> OV
    
    OV --> CC
    OV --> PC
    OV --> MC
    OV --> SC
    
    CM --> FF
    FF --> CPF
    FF --> RPF
    FF --> BF
    FF --> CF
    
    classDef source fill:#e3f2fd,stroke:#0277bd,stroke-width:2px
    classDef management fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef component fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef flags fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class DEF,ENV,FILE,CLI,RT source
    class CM,VP,VAL,OV management
    class CC,PC,MC,SC component
    class FF,CPF,RPF,BF,CF flags
```

## Summary

These architectural diagrams provide a comprehensive view of the Phase 2A optimization system, showing:

1. **Component Integration**: How ConnectionManager and RequestPipeline integrate with existing WebServer infrastructure
2. **Data Flow**: Request processing paths through caching and batching mechanisms
3. **Performance Architecture**: Memory allocation and monitoring systems
4. **Deployment View**: Component placement within Pi Zero 2W constraints
5. **Error Handling**: Recovery strategies and failure modes
6. **Security Boundaries**: Protection layers and access controls
7. **Configuration Management**: Feature flags and gradual rollout capability

The architecture ensures:
- **Backward Compatibility**: Existing functionality remains unchanged
- **Gradual Rollout**: Feature flags enable phased deployment
- **Performance Monitoring**: Comprehensive metrics collection
- **Error Recovery**: Graceful degradation and fallback mechanisms
- **Resource Efficiency**: Optimized for Pi Zero 2W constraints
- **Security**: Multiple protection layers throughout the system