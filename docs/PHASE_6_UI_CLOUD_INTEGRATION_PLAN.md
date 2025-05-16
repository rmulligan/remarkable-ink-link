# Phase 6: UI & Cloud Integration Plan

This phase will focus on making the syntax highlighting feature configurable and accessible via a web interface and integrating it into the broader InkLink ecosystem.

## I. Create Web Interface for Configuration & Interaction

This will be guided by the `docs/web_ui_plan.md` and expanded for syntax highlighting specifics.

### Technology Stack Definition:
- **Frontend**: Nuxt.js (Vue.js-based framework with SSR/SSG capabilities, excellent for modern web applications)
- **Backend**: FastAPI (aligns with the existing Python-based project and provides automatic API documentation)

### Authentication Module (if required for configuration):
- Based on `docs/web_ui_plan.md`, implement UI for reMarkable and MyScript credential input if these are needed to configure or use the syntax highlighting output.
- Develop backend API endpoints (`POST /auth/remarkable`, `POST /auth/myscript`) for secure token/key management.

### Syntax Highlighting Configuration Interface:
- **Theme Selection**:
  - UI to list and select from existing themes (Monokai, Dark, Light, as mentioned in your Phase 2 completion).
- **Custom Theme Support** (see section IV for details):
  - UI for uploading custom theme files.
  - UI to manage (e.g., delete, view details of) custom themes.
- **Interaction/Testing Interface** (optional, for direct use/testing of syntax highlighting):
  - UI for uploading code files or pasting code snippets for highlighting.
  - A "Highlight" button to trigger the process.
  - A display area to show the rendered highlighted code (e.g., as HTML or a preview of Drawj2d output).
  - Option to download the highlighted output or the generated HCL.
- **User Feedback**:
  - Implement clear visual feedback in the UI for operations: status messages (e.g., "Processing...", "Theme Uploaded", "Error") as suggested in `docs/web_ui_plan.md`.

## II. Expose API Endpoints

This will expand on the API structure in `docs/web_ui_plan.md` to specifically cover syntax highlighting.

### Finalize Core API Design:
- Solidify general endpoints from `docs/web_ui_plan.md` if they are prerequisites: authentication, file upload/management (if test files are handled via UI).

### Syntax Highlighting Specific Endpoints:
- `GET /syntax/themes`: Lists all available themes (built-in and custom).
- `POST /syntax/themes`: Allows uploading a new custom theme file.
- `GET /syntax/themes/{theme_name}`: Retrieves details of a specific theme.
- `DELETE /syntax/themes/{theme_name}`: Deletes a custom theme.
- `POST /syntax/highlight`: Accepts a code snippet (and optionally a theme choice) directly in the request body, returns the highlighted output (e.g., HTML, Drawj2d commands, or HCL).
- `POST /syntax/process_file`: Accepts a `file_id` (if using the upload mechanism from `docs/web_ui_plan.md`), applies syntax highlighting, and returns a `response_id` or direct output.

### API Implementation & Documentation:
- Implement the backend logic for these endpoints.
- Ensure robust error handling and consistent JSON responses.
- Generate comprehensive API documentation (e.g., using Swagger/OpenAPI, potentially leveraging the existing `api-docs.json` structure).

## III. Integrate with Existing Pipeline

This involves connecting the now API-enabled syntax highlighting feature with other parts of InkLink.

### Identify Integration Points:
- Clarify how the syntax highlighting (Phases 1-5 components like `AugmentedNotebookServiceV2`, `SyntaxHighlightedInkConverter`, `DocumentService`) will be triggered by or provide services to other parts of the InkLink system.
- Determine if the new UI/API will configure how this integration behaves.

### Cloud Upload Integration (if applicable):
- If notebooks with syntax-highlighted code need to be uploaded to the reMarkable Cloud, the processes in `docs/cloud_integration.md` become key.
- This includes using `rmapi` for file uploads (`put`, `mv`), managing metadata, and implementing retry logic.
- Configuration for `rmapi_path`, `upload_folder`, etc., could be part of the new web UI.

### Service Calls:
- Ensure that other services within InkLink can easily call the new syntax highlighting API endpoints.

## IV. Support Custom Themes (Detailed Implementation)

This expands on the theme support already initiated in Phase 2.

### Define Custom Theme File Format:
- Specify a clear, user-friendly format for custom themes (e.g., JSON or YAML). This file should map token types (e.g., keyword, comment, string, number, identifier) to color values.

### Theme Loading Mechanism:
- Modify `SyntaxHighlightCompilerV2` (and potentially `SyntaxScanner`) to load and parse these custom theme files.
- The system should be able to use either default themes or a user-selected custom theme.

### HCL Generation with Custom Themes:
- Ensure the HCL generation (`Drawj2dService` wrapper) correctly utilizes the colors specified in the active custom theme.

### Storage for Custom Themes:
- Implement a mechanism to store uploaded custom theme files persistently (e.g., in a dedicated directory on the server).

### UI for Theme Management:
- As mentioned in section I, the UI should allow users to upload, view, select, and delete custom themes. A preview feature within the UI would be highly beneficial.

## V. Testing and Deployment

### Comprehensive Testing:
- **Unit Tests**: For all new backend API endpoints, theme management logic, and UI components (if applicable based on frontend framework choice).
- **Integration Tests**: For the end-to-end workflow:
  - Uploading/selecting a theme via UI/API.
  - Processing a code snippet/file.
  - Verifying correct highlighted output based on the selected theme.
  - Testing `rmapi`-based cloud uploads if this integration is part of Phase 6.

### Deployment Strategy:
- Plan the deployment of the web server (e.g., as a Docker container, aligning with the existing `docker-compose.yml`, or other server setup).
- Update any necessary configurations for the production environment.

By following this plan, Phase 6 should successfully deliver a configurable and well-integrated syntax highlighting feature for the InkLink Agentic Framework.