"""Unit test fixtures — synthetic XML/JSON strings for parser/adapter tests."""

import pytest

SCREEN_V2_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<ObjectRepositoryScreenData xmlns="http://schemas.uipath.com/workflow/activities/uix"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <ObjectRepositoryScreenData.Data>
    <TargetApp Version="V2"
        Url="https://example.com/login"
        Selector="&lt;html app='chrome.exe' title='Login' /&gt;"
        BrowserType="Chrome" />
  </ObjectRepositoryScreenData.Data>
</ObjectRepositoryScreenData>
"""

SCREEN_V2_PARAMETERIZED_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<ObjectRepositoryScreenData xmlns="http://schemas.uipath.com/workflow/activities/uix"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <ObjectRepositoryScreenData.Data>
    <TargetApp Version="V2"
        Url="[baseUrl]"
        Selector="&lt;html app='chrome.exe' title='Login' /&gt;"
        BrowserType="Chrome" />
  </ObjectRepositoryScreenData.Data>
</ObjectRepositoryScreenData>
"""

ELEMENT_V6_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<ObjectRepositoryTargetData xmlns="http://schemas.uipath.com/workflow/activities/uix"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <ObjectRepositoryTargetData.Data>
    <TargetAnchorable Version="V6"
        SearchSteps="Selector"
        ScopeSelectorArgument="&lt;html app='chrome.exe' title='Login' /&gt;"
        FullSelectorArgument="&lt;html app='chrome.exe' title='Login' /&gt;&lt;webctrl id='username' /&gt;"
        BrowserURL="https://example.com/login"
        ElementType="InputBox"
        Visibility="Interactive"
        WaitForReadyArgument="Interactive" />
    <x:String x:Key="ActivityType">TypeInto</x:String>
  </ObjectRepositoryTargetData.Data>
</ObjectRepositoryTargetData>
"""

ELEMENT_V6_PARAMETERIZED_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<ObjectRepositoryTargetData xmlns="http://schemas.uipath.com/workflow/activities/uix"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <ObjectRepositoryTargetData.Data>
    <TargetAnchorable Version="V6"
        SearchSteps="Selector"
        ScopeSelectorArgument="&lt;html app='chrome.exe' title='[windowTitle]' /&gt;"
        FullSelectorArgument="&lt;html app='chrome.exe' title='[windowTitle]' /&gt;&lt;webctrl id='username' /&gt;"
        BrowserURL="https://example.com/login"
        ElementType="InputBox" />
    <x:String x:Key="ActivityType">TypeInto</x:String>
  </ObjectRepositoryTargetData.Data>
</ObjectRepositoryTargetData>
"""

METADATA_JSON = """\
{
  "Name": "LoginScreen",
  "Type": "Screen",
  "Id": "screen-001",
  "Reference": "lib/screen-001",
  "ParentRef": "lib/version-001",
  "Created": "2024-01-01T00:00:00Z",
  "Updated": "2024-06-01T00:00:00Z",
  "CreatedBy": ["24.10.0"],
  "UpdatedBy": ["24.10.1"]
}
"""


@pytest.fixture
def screen_v2_content(tmp_path):
    """Write a synthetic Screen V2 .content file and return its path."""
    p = tmp_path / "screen.content"
    p.write_text(SCREEN_V2_XML, encoding="utf-8")
    return p


@pytest.fixture
def screen_v2_parameterized_content(tmp_path):
    """Write a synthetic parameterized Screen V2 .content file and return its path."""
    p = tmp_path / "screen_param.content"
    p.write_text(SCREEN_V2_PARAMETERIZED_XML, encoding="utf-8")
    return p


@pytest.fixture
def element_v6_content(tmp_path):
    """Write a synthetic Element V6 .content file and return its path."""
    p = tmp_path / "element.content"
    p.write_text(ELEMENT_V6_XML, encoding="utf-8")
    return p


@pytest.fixture
def element_v6_parameterized_content(tmp_path):
    """Write a synthetic parameterized Element V6 .content file and return its path."""
    p = tmp_path / "element_param.content"
    p.write_text(ELEMENT_V6_PARAMETERIZED_XML, encoding="utf-8")
    return p


@pytest.fixture
def metadata_file(tmp_path):
    """Write a synthetic .metadata JSON file and return its path."""
    p = tmp_path / ".metadata"
    p.write_text(METADATA_JSON, encoding="utf-8")
    return p
