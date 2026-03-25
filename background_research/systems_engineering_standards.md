# Systems Engineering Standards & SysML v2 Investigation

This document summarizes our technical discussion regarding open standards for systems engineering, with a specific focus on **SysML v2**, lightweight implementations for research environments, and navigating licensing/dependency constraints.

-----

## 1\. Comparison of Open Standards

We weighed the pros and cons of the most prominent open standards used in **Model-Based Systems Engineering (MBSE)**.

| Standard | [SysML](https://en.wikipedia.org/wiki/Systems_modeling_language) | [UML](https://en.wikipedia.org/wiki/Unified_Modeling_Language) | [LML](https://www.google.com/search?q=https://en.wikipedia.org/wiki/Systems_engineering%23Other_tools) |
| :--- | :--- | :--- | :--- |
| **Primary Use** | General Systems Engineering | Software Architecture | Lifecycle Management |
| **Requirements** | Native Support | Limited (Use Cases) | Native Support |
| **Math/Analysis** | Strong (Parametrics) | Weak | Moderate |
| **Pros** | Versatile, huge ecosystem | Developer ubiquity | Low learning curve |
| **Cons** | High complexity (v1.x) | Software-centric | Lower tool adoption |

-----

## 2\. SysML v2 Open Source Ecosystem

SysML v2 represents a shift toward **"Systems as Code"** via a new textual notation. Current open-source and free-tier tools include:

  * **[SysML v2 Pilot Implementation](https://github.com/Systems-Modeling/SysML-v2-Release):** The official OMG reference implementation. Includes Eclipse plugins and a Jupyter Lab kernel.
  * **[Syside Editor (VS Code)](https://sensmetry.com/#products):** A lightweight extension for VS Code that provides a professional textual editing experience.
  * **[Eclipse SysON](https://sysml.org/sysml-tools/):** A web-based graphical modeler built on the [Eclipse](https://github.com/Systems-Modeling/SysML-v2-Release) ecosystem.
  * **[Sysand](https://github.com/sensmetry/sysand):** An open-source (BSD-3-Clause) package manager for SysML v2/KerML, facilitating dependency management similar to `pip`.

-----

## 3\. Lightweight Research Tool Architecture

For environments like **National Labs** where **Java dependencies** and **LGPL licenses** are concerns, a "Sidecar" architecture is recommended to maintain a permissive (BSD/MIT) codebase:

### Component Strategy

1.  **Core Logic:** Built in Python (permissive license).
2.  **Model Interaction:** Use the [SysML v2 API Python Client](https://github.com/Systems-Modeling/SysML-v2-API-Python-Client).
3.  **Isolation:** Run the heavy Java-based [API Services](https://github.com/Systems-Modeling/SysML-v2-API-Services) in a Docker container. Your research tool communicates via REST, preventing license "leakage" and keeping your local environment clean.

### Example Python Integration

Using the API client allows for graph-based traversal of models, similar to [im3synapse](https://github.com/IMMM-SFA/im3synapse):

```python
from sysml_v2_client import Client

# Connect to the isolated API service
client = Client(base_url="http://localhost:9000")

# Query the model as a graph
project = client.get_project_by_name("Research_System")
root = client.get_root_element(project.id)

for rel in root.owned_relationships:
    target = client.get_element(rel.target_id)
    print(f"Subsystem: {target.name}")
```

-----

  ## Next Steps

  Would you like me to draft a **Docker Compose** file to stand up the [SysML v2 API Services](https://github.com/Systems-Modeling/SysML-v2-API-Services) so you can begin testing the Python client?