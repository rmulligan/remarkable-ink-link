# InkLink Control Center - Usage Guide

## Overview

The InkLink Control Center transforms your reMarkable tablet into an interactive command center for managing AI agents, tasks, and projects using natural handwriting and gestures.

## Layout

The control center is organized into five main zones:

```
┌─────────────────────────────────────────────────────────────┐
│                    InkLink Control Center                    │
├─────────────────┬───────────────────┬───────────────────────┤
│    Roadmap      │   Task Board      │   Agent Dashboard    │
│  (Timeline)     │   (Kanban)        │   (Status/Control)   │
├─────────────────┴───────────────────┴───────────────────────┤
│                    Discussion Area                          │
│              (Notes, Commands, Ideas)                       │
├─────────────────────────────────────────────────────────────┤
│                    Quick Actions                           │
│         ⊕ New   ◈ Assign   ↻ Sync   ⚡ Execute            │
└─────────────────────────────────────────────────────────────┘
```

## Gestures & Commands

### Basic Gestures

1. **Circle** - Select an item
   - Draw a circle around any element to select it
   - Selected items can then be moved or modified

2. **Arrow** - Assign or connect
   - Draw arrow from task to agent to assign
   - Draw arrow between milestones to show dependency

3. **Cross-out** - Mark complete
   - Draw X over a task to mark it done
   - Works on tasks, milestones, or checklist items

4. **Box** - Create new item
   - Draw rectangle to create new task/milestone
   - Size determines the element size

5. **Tap** - Activate/toggle
   - Single tap on agents to start/stop
   - Tap quick actions to execute

6. **Double tap** - Expand details
   - Double tap any item to see more information

7. **Question mark** - Query status
   - Draw ? anywhere to refresh that zone
   - Draw ? in empty space for general status

### Text Commands

1. **Agent Commands**
   ```
   @Agent[Limitless]: Process today's recordings
   @Agent[Briefing]: Generate weekly summary
   @Agent[Tracker]: Update project Alpha status
   ```

2. **Task Creation**
   ```
   - Fix authentication bug #urgent #backend
   - Review PR #123 !high
   - Deploy to staging
   ```

3. **Tags and Priorities**
   - Use `#tag` for categorization
   - Use `!priority` for urgency (high, medium, low)
   - Tags can be added to any text

## Zone-Specific Features

### Roadmap Zone

- Draw milestone boxes on timeline
- Connect with arrows for dependencies
- Write inside boxes to add items
- Cross out items to mark complete
- Timeline scrolls horizontally

### Task Board (Kanban)

- Three columns: TODO, DOING, DONE
- Write task in column to create
- Draw arrow to move between columns
- Circle + arrow to assign to agent
- Add tags/priority with # and !

### Agent Dashboard

- Shows real-time agent status
- Tap agent to start/stop
- Circle agent then write command
- Green = running, Orange = processing, Red = error
- Shows last action and next scheduled task

### Discussion Area

- Freeform note-taking space
- Agent commands executed here
- Ideas and brainstorming
- Links to tasks/agents with arrows
- Supports markdown formatting

### Quick Actions

- Tap icons to execute actions
- ⊕ New - Create new task/note
- ◈ Assign - Enter assignment mode
- ↻ Sync - Sync with all systems
- ⚡ Execute - Run selected command
- 📋 Copy - Copy selected item
- 🔍 Search - Search across all zones
- 📊 Stats - View statistics
- ⚙️ Config - Open settings

## Workflows

### Creating and Assigning a Task

1. Write task in TODO column: `- Implement caching #performance`
2. Circle the task to select it
3. Draw arrow to agent (e.g., "Tracker")
4. Agent accepts and begins tracking

### Running Agent Commands

1. Write in discussion area: `@Agent[Limitless]: What did I discuss about caching?`
2. Command is sent to agent
3. Response appears below command
4. Results update relevant zones

### Planning a Milestone

1. Draw box in roadmap zone
2. Write milestone name inside
3. Tap box to add checklist items
4. Connect to other milestones with arrows
5. Progress updates automatically

### Quick Status Check

1. Draw ? in any zone
2. Zone refreshes with latest data
3. All connected systems sync
4. Updated information displays

## Advanced Features

### Multi-Zone Interactions

- Draw arrow from task to milestone to link them
- Circle multiple items then apply bulk action
- Drag items between zones to transform them

### Custom Layouts

- Resize zones by dragging borders
- Hide/show zones with gestures
- Create custom zone arrangements
- Save layouts as templates

### Automation

- Set up trigger-based actions
- Create gesture macros
- Define custom quick actions
- Schedule recurring tasks

## Tips & Tricks

1. **Speed Writing**: Use abbreviations that expand
   - `@AL:` → `@Agent[Limitless]:`
   - `#urg` → `#urgent`

2. **Gesture Shortcuts**: Combine gestures
   - Circle + X = Complete and archive
   - Arrow + ? = Assign and query status

3. **Zone Navigation**: Quick jumps
   - Draw Z pattern to zoom out
   - Pinch to zoom in/out
   - Swipe to switch pages

4. **Template System**: Reusable patterns
   - Save common task structures
   - Create project templates
   - Define workflow patterns

## Troubleshooting

### Sync Issues

- Draw ↻ in quick actions to force sync
- Check agent dashboard for connection status
- Verify network connectivity

### Recognition Problems

- Write more clearly with consistent size
- Use print instead of cursive
- Increase contrast in settings

### Performance

- Limit simultaneous agents
- Clear completed tasks regularly
- Archive old projects

## Best Practices

1. **Daily Routine**
   - Start with status check (?)
   - Review agent dashboard
   - Process discussion notes
   - Plan tasks for the day

2. **Task Management**
   - Keep descriptions concise
   - Use consistent tagging
   - Update status regularly
   - Archive completed work

3. **Agent Coordination**
   - Don't overload single agents
   - Balance workload across agents
   - Monitor performance metrics
   - Adjust priorities as needed

## Keyboard Shortcuts (When Connected)

- `Ctrl+N` - New task
- `Ctrl+A` - Select all in zone
- `Ctrl+S` - Force sync
- `Ctrl+Z` - Undo last action
- `Tab` - Switch zones
- `Enter` - Confirm action
- `Esc` - Cancel operation

## Integration Points

The Control Center integrates with:

- All InkLink agents via MCP
- reMarkable cloud sync
- External task management systems
- Calendar applications
- Note-taking tools
- Development workflows

## Future Enhancements

Planned features include:

- Voice command support
- Predictive task creation
- Advanced analytics
- Custom agent creation
- Collaborative editing
- Export capabilities

---

The InkLink Control Center brings the power of AI agents to your fingertips, literally. Use natural handwriting and intuitive gestures to orchestrate complex workflows with ease.