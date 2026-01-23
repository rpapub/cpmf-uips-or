"""Jinja2 templates for inventory output formats."""

MARKDOWN_TEMPLATE = """\
# Object Repository Inventory

{% for app in apps %}
## {{ app.name }}

{% for version in app.versions %}
### Version: {{ version.name }}

{% for screen in version.screens %}
#### Screen: {{ screen.entry.screen_name }} [{{ screen.entry.descriptor_version }}]

| Attribute | Value |
|-----------|-------|
| **URL** | `{{ screen.entry.url }}` ({% if screen.entry.variable_name %}`[{{ screen.entry.variable_name }}]`{% else %}hardcoded{% endif %}) |
| **Selector** | `{{ screen.entry.selector or '(empty)' }}` |
{% if screen.entry.declared_variables %}| **Variables** | {{ screen.entry.declared_variables|join(', ') }} |
{% endif %}

{% if screen.entry.screenshot %}
![{{ screen.entry.screen_name }}]({{ screenshots_path }}/{{ screen.entry.screenshot }})

{% endif %}
{% if screen.elements %}
**Elements:**

{{ render_elements_md(screen.elements, 0) }}
{% endif %}
{% endfor %}
{% endfor %}
{% endfor %}
"""

MARKDOWN_ELEMENT_TEMPLATE = """\
{% for el in elements %}
{{ indent }}- **{{ el.entry.element_name }}** [{{ el.entry.descriptor_version }}]
{{ indent }}  - Type: {{ el.entry.element_type or 'unknown' }} / {{ el.entry.activity_type or 'unknown' }}
{{ indent }}  - SearchSteps: {{ el.entry.search_steps }}
{{ indent }}  - Visibility: {{ el.entry.visibility or '(not set)' }}
{{ indent }}  - WaitForReady: {{ el.entry.wait_for_ready or '(not set)' }}
{{ indent }}  - Scope: `{{ el.entry.scope_selector[:60] + '...' if el.entry.scope_selector|length > 60 else el.entry.scope_selector or '(empty)' }}`
{{ indent }}  - Selector: `{{ el.entry.full_selector[:60] + '...' if el.entry.full_selector|length > 60 else el.entry.full_selector or '(empty)' }}`
{% if 'FuzzySelector' in el.entry.search_steps %}
{{ indent }}  - Fuzzy: {% if el.entry.fuzzy_selector %}`{{ el.entry.fuzzy_selector[:60] + '...' if el.entry.fuzzy_selector|length > 60 else el.entry.fuzzy_selector }}`{% else %}(configured but empty){% endif %}
{% endif %}
{% if 'Image' in el.entry.search_steps %}
{{ indent }}  - Image: {% if el.entry.has_image %}present{% else %}(configured but empty){% endif %}
{% endif %}
{% if 'CV' in el.entry.search_steps %}
{{ indent }}  - CV: {% if el.entry.has_cv %}{{ el.entry.cv_type or 'present' }}{% else %}(configured but empty){% endif %}
{% endif %}
{% if el.entry.scope_variables or el.entry.selector_variables %}
{{ indent }}  - Variables: {% if el.entry.scope_variables %}scope=[{{ el.entry.scope_variables|join(', ') }}]{% endif %}{% if el.entry.selector_variables %} selector=[{{ el.entry.selector_variables|join(', ') }}]{% endif %}
{% endif %}
{% if el.entry.screenshot %}
{{ indent }}
{{ indent }}  ![{{ el.entry.element_name }}]({{ screenshots_path }}/{{ el.entry.screenshot }})
{{ indent }}
{% endif %}
{% if el.children %}
{{ render_elements_md(el.children, depth + 1) }}
{% endif %}
{% endfor %}
"""


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Object Repository Inventory</title>
    <style>
        :root {
            --bg-color: #ffffff;
            --text-color: #333333;
            --heading-color: #1a1a1a;
            --border-color: #e0e0e0;
            --code-bg: #f5f5f5;
            --screen-bg: #f8f9fa;
            --element-bg: #ffffff;
            --status-hardcoded: #dc3545;
            --status-param: #28a745;
        }
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: var(--bg-color);
        }
        h1 { color: var(--heading-color); border-bottom: 2px solid var(--border-color); padding-bottom: 10px; }
        h2 { color: var(--heading-color); margin-top: 30px; }
        h3 { color: var(--heading-color); margin-top: 20px; }
        .screen {
            background: var(--screen-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }
        .screen-header { display: flex; justify-content: space-between; align-items: center; }
        .screen-name { font-size: 1.2em; font-weight: 600; margin: 0; }
        .screen-meta { font-size: 0.9em; color: #666; }
        .screen-url { font-family: monospace; background: var(--code-bg); padding: 2px 6px; border-radius: 3px; word-break: break-all; }
        .selector-code { font-family: monospace; background: var(--code-bg); padding: 2px 6px; border-radius: 3px; word-break: break-all; font-size: 0.85em; display: inline-block; max-width: 100%; overflow-x: auto; }
        .version-badge { font-size: 0.7em; color: #666; font-weight: normal; }
        .screen-screenshot { max-width: 100%; margin: 10px 0; border: 1px solid var(--border-color); border-radius: 4px; }
        .elements { margin-top: 15px; }
        .elements-title { font-weight: 600; margin-bottom: 10px; }
        .element {
            background: var(--element-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 10px;
            margin: 8px 0;
            margin-left: var(--indent, 0);
        }
        .element-header { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
        .element-name { font-weight: 600; }
        .element-type { font-size: 0.85em; color: #666; }
        .element-details { font-size: 0.85em; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-color); }
        .element-details div { margin: 4px 0; }
        .element-screenshot { max-width: 100%; max-height: 200px; margin: 8px 0; border: 1px solid var(--border-color); border-radius: 4px; }
        .status {
            font-size: 0.75em;
            padding: 2px 8px;
            border-radius: 10px;
            font-weight: 500;
        }
        .status-hardcoded { background: #ffeef0; color: var(--status-hardcoded); }
        .status-parameterized { background: #e6ffed; color: var(--status-param); }
        .nested { margin-left: 20px; border-left: 2px solid var(--border-color); padding-left: 15px; }
    </style>
</head>
<body>
    <h1>Object Repository Inventory</h1>

{% for app in apps %}
    <h2>{{ app.name }}</h2>

{% for version in app.versions %}
    <h3>Version: {{ version.name }}</h3>

{% for screen in version.screens %}
    <div class="screen">
        <div class="screen-header">
            <h4 class="screen-name">{{ screen.entry.screen_name }} <span class="version-badge">[{{ screen.entry.descriptor_version }}]</span></h4>
            <span class="status {% if screen.entry.variable_name %}status-parameterized{% else %}status-hardcoded{% endif %}">
                {% if screen.entry.variable_name %}[{{ screen.entry.variable_name }}]{% else %}hardcoded{% endif %}
            </span>
        </div>
        <div class="screen-meta">
            <div><strong>URL:</strong> <code class="screen-url">{{ screen.entry.url }}</code></div>
            <div><strong>Selector:</strong> <code class="selector-code">{{ screen.entry.selector or '(empty)' }}</code></div>
{% if screen.entry.declared_variables %}
            <div><strong>Variables:</strong> {{ screen.entry.declared_variables|join(', ') }}</div>
{% endif %}
        </div>
{% if screen.entry.screenshot %}
        <img class="screen-screenshot" src="{{ screenshots_path }}/{{ screen.entry.screenshot }}" alt="{{ screen.entry.screen_name }}">
{% endif %}
{% if screen.elements %}
        <div class="elements">
            <div class="elements-title">Elements:</div>
{{ render_elements_html(screen.elements, 0)|safe }}
        </div>
{% endif %}
    </div>
{% endfor %}
{% endfor %}
{% endfor %}
</body>
</html>
"""

HTML_ELEMENT_TEMPLATE = """\
{% for el in elements %}
            <div class="element" style="--indent: {{ depth * 20 }}px; margin-left: {{ depth * 20 }}px;">
                <div class="element-header">
                    <span class="element-name">{{ el.entry.element_name }} <span class="version-badge">[{{ el.entry.descriptor_version }}]</span></span>
                    <span class="element-type">{{ el.entry.element_type or 'unknown' }} / {{ el.entry.activity_type or 'unknown' }}</span>
                    <span class="status {% if el.entry.is_parameterized %}status-parameterized{% else %}status-hardcoded{% endif %}">
                        {% if el.entry.is_parameterized %}parameterized{% else %}hardcoded{% endif %}
                    </span>
                </div>
                <div class="element-details">
                    <div><strong>SearchSteps:</strong> {{ el.entry.search_steps }}</div>
                    <div><strong>Visibility:</strong> {{ el.entry.visibility or '(not set)' }}</div>
                    <div><strong>WaitForReady:</strong> {{ el.entry.wait_for_ready or '(not set)' }}</div>
                    <div><strong>Scope:</strong> <code class="selector-code">{{ el.entry.scope_selector or '(empty)' }}</code></div>
                    <div><strong>Selector:</strong> <code class="selector-code">{{ el.entry.full_selector or '(empty)' }}</code></div>
{% if 'FuzzySelector' in el.entry.search_steps %}
                    <div><strong>Fuzzy:</strong> {% if el.entry.fuzzy_selector %}<code class="selector-code">{{ el.entry.fuzzy_selector }}</code>{% else %}<em>(configured but empty)</em>{% endif %}</div>
{% endif %}
{% if 'Image' in el.entry.search_steps %}
                    <div><strong>Image:</strong> {% if el.entry.has_image %}present{% else %}<em>(configured but empty)</em>{% endif %}</div>
{% endif %}
{% if 'CV' in el.entry.search_steps %}
                    <div><strong>CV:</strong> {% if el.entry.has_cv %}{{ el.entry.cv_type or 'present' }}{% else %}<em>(configured but empty)</em>{% endif %}</div>
{% endif %}
{% if el.entry.scope_variables or el.entry.selector_variables %}
                    <div><strong>Variables:</strong> {% if el.entry.scope_variables %}scope=[{{ el.entry.scope_variables|join(', ') }}]{% endif %}{% if el.entry.selector_variables %} selector=[{{ el.entry.selector_variables|join(', ') }}]{% endif %}</div>
{% endif %}
                </div>
{% if el.entry.screenshot %}
                <img class="element-screenshot" src="{{ screenshots_path }}/{{ el.entry.screenshot }}" alt="{{ el.entry.element_name }}">
{% endif %}
{% if el.children %}
                <div class="nested">
{{ render_elements_html(el.children, depth + 1)|safe }}
                </div>
{% endif %}
            </div>
{% endfor %}
"""
