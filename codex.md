# Codex Project Guide: InkLink

This repo is for InkLink — a toolkit that enables users to interact with AI directly from their reMarkable tablet.

Primary project goals:
- Convert AI and web responses into editable ink layers (.rm files)
- Allow tagging of pages to trigger workflows (e.g., #summarize, #calendar)
- Enable automatic sync to/from reMarkable via `rmapi`
- Support modular AI tool interaction via MCP

Important repo structure:
- `scripts/` → CLI tools for syncing, formatting, task extraction, etc.
- `formatters/` → drawj2d-compatible layout generators
- `handlers/` → AI-triggered tools (summarizers, entity extractors, calendar sync, etc.)
- `config/` → MCP tool definitions and user preferences

Dev Notes:
- Codex can use the ddvk fork of `rmapi` located at `~/Projects/rmapi`
- Target `.rm` file generation from markdown or text output
- Use prompt-based generation of HCL layout where needed
- If CLI scaffolding is needed, make it cross-platform where possible (macOS + Linux)

Style Guidelines:
- Be modular and testable
- Favor `stdin`/`stdout` communication where possible (MCP-friendly)
- If AI responses are generated, format for reMarkable-appropriate layout and readability

Research Report: reMarkable Application Development
Objective: To provide the necessary technical information for developing a reMarkable tablet application that extracts handwriting stroke data, utilizes the MyScript Cloud Platform (MCP) for handwriting recognition (HWR), integrates AI for knowledge graph processing, and aims for persistence across reMarkable software updates.
1. Extracting Lines V6 Stroke Data from the RM Scene Library
The primary tool for interacting with reMarkable's .rm notebook files (which contain the handwriting data) outside the tablet is the ricklupton/rmscene Python library.
1.1. ricklupton/rmscene Library:
Repository: https://github.com/ricklupton/rmscene
Purpose: Parses reMarkable .rm files (version 3, 4, 5, and 6 line formats) into Python objects, allowing access to metadata, layers, and stroke data.
Installation: Typically installed via pip:
pip install rmscene


1.2. Accessing Stroke Data:
Core Function: The read_rm_file() function loads the .rm file.
import rmscene

# Load the notebook file
notebook_path = 'path/to/your/notebook.rm'
notebook = rmscene.read_rm_file(notebook_path)

# Access pages (scenes)
for page_id, page in notebook.scenes.items():
    # Access layers within a page
    for layer in page.layers:
        # Access strokes within a layer
        for stroke in layer.strokes:
            # 'stroke' object contains the data
            print(f"Stroke color: {stroke.colour}, width: {stroke.width_px}")
            # Access individual points in the stroke
            for point in stroke.points:
                # 'point' object has coordinates, pressure, etc.
                # print(point) # See structure below
                pass


Relevant Classes:
rmscene.RMNotebook: Represents the entire notebook file.
rmscene.Scene: Represents a single page.
rmscene.Layer: Represents a drawing layer on a page.
rmscene.Stroke: Represents a single continuous handwriting stroke. This is the key object containing Lines V6 data.
rmscene.Point: Represents a single data point within a stroke.
1.3. Lines V6 Stroke Data Structure (rmscene.Stroke and rmscene.Point):
The rmscene library parses the binary Lines V6 format into accessible Python objects. A Stroke object contains metadata and a list of Point objects.
rmscene.Stroke Attributes (Examples):
colour: Enum representing the stroke color (BLACK, GREY, WHITE).
tool: Enum representing the drawing tool used.
width_px: The stroke width in pixels.
points: A list of rmscene.Point objects.
rmscene.Point Attributes (Lines V6): Each point in the stroke.points list typically has the following attributes:
x: Float, X-coordinate.
y: Float, Y-coordinate.
speed: Float, Speed at this point.
direction: Float, Direction (angle) at this point.
width: Float, Width modifier at this point.
pressure: Float, Pen pressure at this point.
Conceptual Data Example (Python representation):
# Example structure after parsing with rmscene
stroke = Stroke(
    colour=Colour.BLACK,
    tool=Tool.FINELINER_V2,
    width_px=2.0,
    points=[
        Point(x=100.5, y=200.1, speed=10.2, direction=1.57, width=0.8, pressure=0.7),
        Point(x=102.3, y=201.5, speed=12.5, direction=1.60, width=0.8, pressure=0.75),
        # ... more points
    ]
)


1.4. Dependencies and Prerequisites:
Python: Requires a compatible Python installation (check rmscene documentation for specific versions, generally Python 3.7+).
Libraries: rmscene depends on libraries like numpy for numerical operations. pip handles these dependencies automatically.
1.5. Performance Considerations:
Parsing large .rm files with many strokes can be memory and CPU intensive.
Processing should ideally happen off-device (e.g., on a companion computer or server) unless the on-device application is carefully optimized. If running on the device, resource constraints (CPU, RAM) are significant.
2. Utilizing the MyScript Cloud Platform (MCP) for Handwriting Recognition
MCP provides REST APIs for converting handwriting stroke data into recognized text, shapes, math equations, etc.
2.1. Requirements:
MyScript Developer Account: Sign up at https://developer.myscript.com/.
API Keys: Obtain an Application Key and an HMAC Key from your MyScript developer account dashboard. These are required for authentication.
Understanding Usage: Familiarize yourself with the transaction limits, pricing tiers, and usage policies associated with your account/plan.
2.2. API Interaction Workflow:
Format Stroke Data: Convert the extracted Lines V6 stroke data (specifically the x, y, and potentially t for time if available/needed) into the JSON format required by the MyScript API.
Construct Request: Create an HTTP POST request to the appropriate MyScript API endpoint. Include authentication headers and the JSON payload containing the stroke data.
Send Request: Send the request to the MCP server.
Process Response: Receive the JSON response containing the recognition results (text candidates, scores, etc.) or error messages.
2.3. Key API Details:
Endpoints: The primary endpoint for standard text recognition is typically part of the "REST v4" API. The exact URL might look something like: https://cloud.myscript.com/api/v4.0/iink/batch (for batch processing) or potentially a streaming endpoint if needed. Refer to the official MyScript API documentation for the precise endpoints for "Text Document" recognition.
Authentication: Requests must include specific HTTP headers containing your Application Key and a computed HMAC signature (using your HMAC Key and parts of the request data) for security. MyScript provides detailed documentation and examples on how to calculate the HMAC signature.
Data Format (Input): MyScript generally expects stroke data as a JSON object. The exact structure depends on the recognition type (Text, Shape, Math, etc.). For text, it typically involves defining the input type ("TEXT"), providing configuration (language, etc.), and supplying the stroke data as an array of strokes, where each stroke is an array of points (x, y coordinates).
Mapping Lines V6 to MyScript: You will need to map the x and y coordinates from the rmscene.Point objects. MyScript might also accept timestamps (t) for points if available, though rmscene doesn't directly expose timestamps from Lines V6. You might need to infer timing based on point order or omit it.
Conceptual JSON Input Snippet (Illustrative - check MyScript docs for exact format):
{
  "configuration": {
    "lang": "en_US",
    "text": {
      "guides": { "enable": false }
    }
  },
  "contentType": "Text", // Specify recognition type
  "strokeGroups": [ // Often represents logical blocks of writing
    {
      "strokes": [
        { // First stroke
          "x": [100.5, 102.3, /* ... */],
          "y": [200.1, 201.5, /* ... */]
          // "t": [timestamp1, timestamp2, /* ... */] // Optional if available
        },
        { // Second stroke
          "x": [150.0, 151.2, /* ... */],
          "y": [210.5, 211.8, /* ... */]
        }
        // ... more strokes
      ]
    }
  ]
}


Data Format (Output): The response is typically JSON containing recognition candidates, confidence scores, and potentially bounding boxes.
2.4. Rate Limits and Usage:
MCP APIs have rate limits (requests per second/minute) and usage quotas (number of transactions per month) based on the subscription plan.
The application must handle potential rate-limiting errors (e.g., HTTP 429 Too Many Requests) gracefully, possibly by implementing backoff and retry mechanisms.
Consider the cost implications of frequent API calls.
3. Developing Persistent Applications on the reMarkable Tablet
Developing applications that survive reMarkable's system updates is challenging due to the tablet's locked-down nature and the way updates often replace system partitions. There is no official SDK, and development relies on community tools and reverse engineering.
3.1. Development Environment & Access:
SSH Access: Required for deploying and managing applications. This is typically enabled through the reMarkable's settings menu.
Cross-Compilation: Applications usually need to be cross-compiled for the ARM architecture of the reMarkable processor (typically using a toolchain like Linaro or building within a compatible Docker container).
Languages: Common choices include C, C++, Go, Rust, and Python (often via Entware/Toltec). The choice depends on performance needs and available libraries.
3.2. Persistence Strategies & Challenges:
Updates Overwrite System Partitions: reMarkable updates often replace the root filesystem (/), meaning applications installed in standard locations like /usr/bin or /usr/lib will likely be deleted.
/home/root: This directory usually persists across updates and is the safest place to store application binaries, configuration files, and user data. However, even this isn't absolutely guaranteed.
/opt Directory (Toltec/Entware):
Toltec: (https://github.com/toltec-dev/toltec) is a community package manager for reMarkable. It installs packages (including applications, libraries, and dependencies like Python) into /opt. Toltec has mechanisms designed to help packages survive updates, often involving re-installation scripts. This is generally the recommended approach for managing dependencies and achieving better persistence.
Entware: A broader embedded Linux package repository, sometimes used on reMarkable, also often installs to /opt. Persistence relies on similar mechanisms as Toltec or manual re-installation.
Application Packaging: Package the application using the Toltec format if possible. This leverages the community's efforts towards maintaining persistence.
Systemd Services: Custom applications can be run as services using systemd. Service definition files are typically placed in /etc/systemd/system/ or /home/root/.config/systemd/user/. While /etc is often overwritten, user services defined under /home/root might be easier to restore or reactivate post-update. Toltec often handles service management for its packages.
Launchers: Community launchers (e.g., remux, Oxide, Draft) provide alternative interfaces to launch applications. Integrating with these might offer a more stable entry point than relying solely on systemd services that could be disrupted by updates.
Update Scripts: Some developers create scripts that run after a system update to automatically reinstall or re-link their applications from /home/root or a backup location. This requires manual intervention or clever hooking into the update process, which is fragile.
3.3. Insights from ddvk Repositories:
ddvk/rmapi (https://github.com/ddvk/rmapi):
Provides a Go library and command-line tool for interacting with the reMarkable cloud, filesystem, and some device functions.
Studying its code reveals how to interact with the device's file structure (/home/root/.local/share/remarkable/xochitl/ for notebooks), read device status, and potentially interact with the xochitl process (the main UI).
It demonstrates practical interaction patterns with the reMarkable system from an application running on the device, which is valuable context even if not directly solving persistence.
ddvk/rmapi-hwr (https://github.com/ddvk/rmapi-hwr):
An example application (using rmapi) that performs on-device HWR using the Tesseract OCR engine (not MyScript).
Demonstrates:
Reading notebook files directly on the device.
Processing stroke data (converting to an image format suitable for Tesseract).
Running an external process (Tesseract) on the device.
Writing results back (e.g., as text layers or separate files).
This provides a concrete example of an application running within the reMarkable environment, showing how file access and processing might be structured. It highlights the feasibility of running complex tasks on the device, albeit with performance considerations (Tesseract on-device is slower than cloud HWR).
3.4. Best Practices Summary for Persistence:
Use Toltec: Leverage the Toltec package manager for installation and dependency management. Package your application for Toltec if possible.
Install to /opt (via Toltec) or /home/root: Avoid standard system directories.
Store Data in /home/root: Keep user data and configuration separate from application binaries in a persistent location.
Prepare for Reinstallation: Assume the application might need to be reinstalled or re-enabled after an update. Design it accordingly.
Minimize System Modifications: Avoid deep changes to the root filesystem. Stick to user-space applications and standard Toltec/Entware practices.
Monitor Community: Stay updated with reMarkable development communities (e.g., Reddit r/RemarkableTablet, Discord servers) for the latest techniques and tool updates.
4. Knowledge Graph Integration
Integrating AI for knowledge graph processing is largely independent of the reMarkable-specific challenges, aside from where the processing occurs.
On-Device: If the KG processing logic is simple enough or libraries are available (e.g., Python libraries installable via Toltec), it could run directly on the tablet. This requires careful resource management.
Off-Device: More complex AI/KG processing is better suited for a companion server or cloud service. The reMarkable application would extract/send the recognized text (from MCP) to this external service, which would handle KG construction/querying and send results back to the tablet app for display.
Implementation: This involves standard software development practices: choosing appropriate KG databases (Neo4j, RDF stores) or libraries (RDFLib, NetworkX), designing the data model, and implementing the logic to process text and interact with the KG.
5. Summary and Key Considerations
Stroke Extraction: ricklupton/rmscene is the key Python library for reading .rm files and accessing Lines V6 stroke data off-device. On-device access requires different methods, potentially interacting directly with the file format or using libraries like rmapi.
MCP Integration: Requires careful formatting of stroke data (X, Y coordinates) into JSON, handling API key authentication (Application Key + HMAC), and managing rate limits/usage quotas. Use the official MyScript developer documentation for exact API specifications.
Persistence: This is the most significant challenge. Using Toltec is the most robust community approach. Store application binaries and especially user data in /home/root or /opt (via Toltec). Be prepared for potential breakage after system updates.
Development Environment: Requires cross-compilation and SSH access. Toltec simplifies dependency management.
Resource Limits: The reMarkable tablet has limited CPU and RAM. On-device processing (HWR, complex AI) must be carefully optimized or offloaded.
Unofficial Nature: All development on the reMarkable platform is unofficial and subject to change without notice by reMarkable AS.
This report provides the foundational technical information. The coding agent will need to consult the specific documentation for rmscene, MyScript Cloud Platform API, Toltec, and any chosen AI/KG libraries during development.
