# GitHub Copilot Custom Agents

This directory contains custom agent configurations for GitHub Copilot workspace. Custom agents provide specialized expertise for specific tasks and domains.

---

## Overview

Custom agents are specialized AI assistants with domain-specific knowledge and tools. They are invoked as tools by the main Copilot agent to handle tasks requiring specialized expertise.

**Key Benefits**:
- Domain-specific knowledge and context
- Specialized tooling and capabilities
- Independent context windows
- Higher quality results for specialized tasks

---

## Available Agents

### my-agent (Principal Engineer)

**Type**: Principal-level Software Engineering Agent
**Expertise**: Engineering excellence, technical leadership, pragmatic implementation
**File**: [my-agent.md](my-agent.md)

**Capabilities**:
- Software architecture and design
- Engineering best practices
- Technical decision-making
- Code review and quality assessment
- Performance optimization
- Pragmatic implementation strategies

**When to Use**:
- Complex architectural decisions
- Engineering trade-off analysis
- Technical leadership guidance
- Code review feedback
- System design questions
- Best practice recommendations

**Example Invocations**:
```
"Review this architecture and suggest improvements"
"What's the best approach for implementing X feature?"
"Evaluate the trade-offs between approach A and B"
"Provide engineering guidance on code structure"
```

---

### security-agent (Security Expert)

**Type**: Application Security Specialist
**Expertise**: Vulnerability assessment, secure coding, OWASP Top 10, Python security
**File**: [security-agent.md](security-agent.md)

**Capabilities**:
- Security vulnerability scanning and assessment
- Input validation and sanitization
- Authentication and authorization best practices
- Cryptographic operations and secure random generation
- API security (bearer tokens, rate limiting, CORS)
- IoT/embedded system security hardening
- Dependency vulnerability auditing

**When to Use**:
- Security code reviews
- Vulnerability assessment and remediation
- Implementing authentication/authorization
- Hardening API endpoints
- Secure configuration for Raspberry Pi deployment
- Reviewing third-party dependencies for vulnerabilities

**Example Invocations**:
```
"Review this endpoint for security vulnerabilities"
"How should I securely validate bearer tokens?"
"Assess security risks in this ICS parsing code"
"Provide security hardening recommendations for systemd service"
```

---

### ics-calendar-agent (ICS Calendar Expert)

**Type**: Calendar Format and Processing Specialist
**Expertise**: RFC 5545 (iCalendar), RRULE recurrence, timezone handling
**File**: [ics-calendar-agent.md](ics-calendar-agent.md)

**Capabilities**:
- ICS/iCalendar format parsing and validation
- RRULE recurrence rule expansion and edge cases
- Timezone conversion and DST handling
- Calendar provider specifics (Microsoft 365, Google, iCloud)
- Event filtering and date range processing
- Performance optimization for calendar processing

**When to Use**:
- ICS parsing and validation issues
- RRULE expansion problems or edge cases
- Timezone conversion bugs
- Calendar-specific feature implementation
- Event filtering and prioritization
- Performance issues with calendar processing

**Example Invocations**:
```
"Fix this RRULE expansion to handle last Friday of month"
"Why are all-day events showing with time components?"
"Optimize this calendar parsing for large ICS files"
"Handle timezone conversion for recurring events across DST"
```

---

### performance-agent (Performance Expert)

**Type**: Performance Optimization Specialist
**Expertise**: Raspberry Pi optimization, memory efficiency, async I/O
**File**: [performance-agent.md](performance-agent.md)

**Capabilities**:
- Memory optimization for resource-constrained systems
- CPU efficiency and algorithmic optimization
- Async I/O patterns and best practices
- Caching strategies and implementation
- Startup time optimization
- Runtime monitoring and graceful degradation
- Raspberry Pi Zero 2W specific tuning

**When to Use**:
- High memory usage issues
- Slow response times or request latency
- CPU bottlenecks and performance profiling
- Optimizing startup time
- Implementing efficient caching
- Resource exhaustion problems
- Performance testing and benchmarking

**Example Invocations**:
```
"Reduce memory usage in calendar refresh process"
"Optimize this RRULE expansion for faster processing"
"Implement efficient caching for ICS feeds"
"Profile and fix performance bottleneck in event filtering"
```

---

## Using Custom Agents

### From Main Copilot Agent

Custom agents appear as tools in the main agent's toolkit. The main agent can invoke them as needed:

```
Tool: my-agent
Parameters:
  prompt: "Your question or task description"
```

### Best Practices

1. **Provide Context**: Give the agent enough context about the problem
2. **Be Specific**: Clear, focused questions get better answers
3. **Full Task Delegation**: Let the agent do the work, don't just ask for advice
4. **Trust the Results**: Agents are specialized experts - trust their output

### When to Use Custom Agents

**DO use custom agents when**:
- Task matches their domain expertise
- Need specialized knowledge
- Complex technical decisions required
- Architecture or design questions
- Code quality assessment needed

**DON'T use custom agents when**:
- Simple, straightforward tasks
- Agent's domain doesn't match the task
- Quick factual lookup needed

---

## Agent Architecture

### How Custom Agents Work

1. **Invocation**: Main agent calls custom agent as a tool
2. **Context Transfer**: Problem statement and context passed to agent
3. **Independent Processing**: Agent works in its own context window
4. **Result Return**: Agent returns completed work or analysis
5. **Integration**: Main agent integrates results

### Context Management

- **Private Context**: Each agent has its own context window
- **Stateless**: Each invocation starts fresh
- **No Memory**: Agents don't remember previous invocations
- **Context Transfer Required**: Must pass all necessary context in the prompt

---

## Adding New Custom Agents

To add a new custom agent:

1. **Create Agent Definition**: Create `{agent-name}.md` in this directory
2. **Define Expertise**: Clearly specify domain and capabilities
3. **Document Usage**: Explain when and how to use the agent
4. **Test**: Verify agent works as expected
5. **Update This README**: Add agent to the list above

### Agent Definition Template

```markdown
# {Agent Name}

## Purpose
Brief description of agent's purpose and expertise

## Capabilities
- Capability 1
- Capability 2
- Capability 3

## When to Use
Explain situations where this agent should be invoked

## Example Prompts
- "Example prompt 1"
- "Example prompt 2"

## Instructions
Detailed instructions for the agent's behavior...
```

---

## Guidelines for Main Agent

When deciding whether to use a custom agent:

1. **Check Expertise Match**: Does the agent's domain match the task?
2. **Prefer Agents for Specialty Work**: Use agents for their specialty areas
3. **Full Delegation**: Instruct agent to do the work, not just advise
4. **Accept Results**: Don't second-guess specialized agent output
5. **Sequential Use**: One agent at a time for focused results

---

## Agent Coordination

### Multiple Agents

If a task requires multiple agents:
1. Break task into domain-specific parts
2. Invoke agents sequentially
3. Integrate results
4. Maintain overall coherence

### Agent vs. Direct Execution

**Use Agent**:
- Complex technical decisions
- Domain-specific expertise needed
- Quality assessment required
- Architecture/design questions

**Direct Execution**:
- Simple, well-defined tasks
- No specialized expertise needed
- Quick factual changes
- Routine operations

---

## Limitations

**Custom agents cannot**:
- Remember previous invocations
- Share context between invocations
- Access files directly (context must be provided)
- Execute code or use tools directly
- Coordinate with each other automatically

**Custom agents can**:
- Provide expert analysis and recommendations
- Make complex technical decisions
- Review and assess code quality
- Design architectures and systems
- Explain trade-offs and best practices

---

## Feedback and Improvements

To improve agent effectiveness:

1. **Clear Prompts**: Provide clear, specific questions
2. **Sufficient Context**: Include all necessary context
3. **Focused Tasks**: One task per invocation
4. **Iterative Refinement**: Adjust prompts based on results
5. **Document Learnings**: Update agent instructions based on experience

---

**Last Updated**: 2025-11-08
**Number of Agents**: 4 (my-agent, security-agent, ics-calendar-agent, performance-agent)
**For Main Documentation**: See [../.github/copilot-instructions.md](../copilot-instructions.md)
