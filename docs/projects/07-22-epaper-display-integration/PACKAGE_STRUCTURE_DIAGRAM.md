# Package Structure and Integration Diagram

## Package Structure

```mermaid
classDiagram
    class DisplayAbstractionLayer {
        <<interface>>
        +initialize() bool
        +render(content: Any) bool
        +clear() bool
        +shutdown() bool
        +get_capabilities() DisplayCapabilities
    }
    
    class DisplayCapabilities {
        +width: int
        +height: int
        +colors: int
        +supports_partial_update: bool
        +supports_grayscale: bool
        +supports_red: bool
    }
    
    class Region {
        +x: int
        +y: int
        +width: int
        +height: int
        +contains_point(x: int, y: int) bool
        +overlaps(other: Region) bool
    }
    
    class EInkDisplayDriver {
        <<interface>>
        +partial_update(region: Region, buffer: bytes) bool
        +full_update(buffer: bytes) bool
        +sleep() bool
        +wake() bool
    }
    
    class WaveshareEPaperDriver {
        -spi: SpiDev
        -width: int
        -height: int
        -initialized: bool
        +initialize() bool
        +render(content: bytes) bool
        +clear() bool
        +shutdown() bool
        +get_capabilities() DisplayCapabilities
        +partial_update(region: Region, buffer: bytes) bool
        +full_update(buffer: bytes) bool
        +sleep() bool
        +wake() bool
    }
    
    class RefreshStrategyManager {
        -driver: EInkDisplayDriver
        -last_full_refresh_time: datetime
        -partial_update_count: int
        +determine_refresh_strategy(changed_regions: List[Region]) RefreshStrategy
        +apply_refresh_strategy(strategy: RefreshStrategy, buffer: bytes, changed_regions: List[Region]) bool
    }
    
    class DiffBasedUpdateDetector {
        -display_width: int
        -display_height: int
        -previous_content: str
        -section_map: Dict[str, Region]
        +detect_changes(new_content: str) List[Region]
        +requires_full_refresh(new_content: str) bool
    }
    
    class TextRenderingOptimizer {
        -min_font_size: int
        -optimized_fonts: List[str]
        -font_size_mapping: Dict[str, int]
        +optimize_html_for_eink(html_content: str) str
        +get_optimized_font_family() str
        +adjust_font_size_for_eink(element_type: str, original_size: Optional[int]) int
    }
    
    class EInkWhatsNextRenderer {
        -text_optimizer: TextRenderingOptimizer
        -diff_detector: DiffBasedUpdateDetector
        -previous_html: str
        +render_events(events: List[CachedEvent], status_info: Optional[Dict[str, Any]], refresh_manager: Optional[RefreshStrategyManager]) Dict[str, Any]
        +render_error(error_message: str, cached_events: Optional[List[CachedEvent]]) Dict[str, Any]
        +render_authentication_prompt(verification_uri: str, user_code: str) Dict[str, Any]
    }
    
    DisplayAbstractionLayer <|-- EInkDisplayDriver
    EInkDisplayDriver <|-- WaveshareEPaperDriver
    WaveshareEPaperDriver --> DisplayCapabilities
    WaveshareEPaperDriver --> Region
    RefreshStrategyManager --> EInkDisplayDriver
    RefreshStrategyManager --> Region
    DiffBasedUpdateDetector --> Region
    EInkWhatsNextRenderer --> TextRenderingOptimizer
    EInkWhatsNextRenderer --> DiffBasedUpdateDetector
    EInkWhatsNextRenderer --> RefreshStrategyManager
```

## Integration with CalendarBot

```mermaid
flowchart TD
    A[CalendarBot Application] --> B[RendererFactory]
    B --> C{Renderer Type}
    C -->|html| D[HTMLRenderer]
    C -->|whats-next| E[WhatsNextRenderer]
    C -->|eink-whats-next| F[EInkWhatsNextRenderer]
    F --> G[calendarbot_epaper Package]
    G --> H[Display Abstraction Layer]
    H --> I[Waveshare Driver]
    I --> J[Physical e-Paper Display]
    F --> K[Text Rendering Optimizer]
    F --> L[Diff-Based Update Detector]
    F --> M[Refresh Strategy Manager]
```

## Package Installation and Deployment

```mermaid
flowchart TD
    A[Development Environment] --> B[Create Package]
    B --> C[Test in Virtual Environment]
    C --> D{Tests Pass?}
    D -->|No| B
    D -->|Yes| E[Build Package]
    E --> F[Deploy to Raspberry Pi]
    F --> G[Install Package]
    G --> H[Run CalendarBot with e-Paper Support]
    H --> I[Verify Display Output]