import os
import re

def test_phase5a2_traceability_guard():
    # Parse the markdown file
    docs_path = os.path.join(os.path.dirname(__file__), "..", "docs", "phase_5a2_test_traceability.md")
    with open(docs_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all table rows
    rows = re.findall(r'\|\s*\*\*P5A2-(\d{3})\*\*\s*\|.*?\|\s*`([^`]+)`\s*\|\s*([A-Z]+)\s*\|', content)
    
    print('LENGTH:', len(content))
    print(repr(content[:200]))
    ids_found = []
    nodes = []
    
    for row in rows:
        contract_num = int(row[0])
        node_id = row[1]
        status = row[2]
        
        ids_found.append(contract_num)
        nodes.append(node_id)
        assert status == "COVERED", f"Contract P5A2-{row[0]} is not COVERED"

    # Exact IDs P5A2-001..P5A2-040
    expected_ids = list(range(1, 41))
    assert sorted(ids_found) == expected_ids, f"IDs mismatch. Missing or extra IDs found."
    assert len(set(ids_found)) == 40, "Duplicate IDs found."

    # Validate that every mapped pytest node exists
    import pytest
    class CollectPlugin:
        def __init__(self):
            self.collected = []
        def pytest_collection_modifyitems(self, items):
            for item in items:
                self.collected.append(item.nodeid)

    plugin = CollectPlugin()
    pytest.main(["-q", "--collect-only", "tests/"], plugins=[plugin])
    
    collected_node_names = [n.split("::")[-1] for n in plugin.collected]
    
    for node in nodes:
        node_name = node.split("::")[-1]
        assert node_name in collected_node_names, f"Mapped node {node} does not exist in collected tests"
