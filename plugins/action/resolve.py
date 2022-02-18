# Make coding more python3-ish
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.errors import AnsibleError
from ansible.module_utils.six import string_types
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible.utils.vars import merge_hash

from ansible_collections.tosit.tdp.plugins.module_utils.constants import (
    PREFIX,
    SEPARATOR_CHAR,
)

display = Display()

MANDATORY_GROUPS = [PREFIX + "all", PREFIX + "hadoop"] 

# Example:
#   node_name: hdfs_datanode_conf
#   result: ["all", "hadoop", "hdfs", "hdfs_datanode", "hdfs_datanode_conf"]
def get_node_groups_from_node_name(node_name):
    splits = node_name.split(SEPARATOR_CHAR)
    node_groups = [PREFIX + splits[0]]
    for i, split_value in enumerate(splits[1:], start=1):
        node_groups.append(node_groups[i - 1] + SEPARATOR_CHAR + split_value)
    return node_groups


def sort_groups(groups, node_groups):
    # sort should be lexicographically correct as long there are no caps involved
    # if we want to assure lexicographic order, we can add parameter key=str.lower
    # which will apply the lower() function to every strings
    return sorted(set(groups).intersection(node_groups))


class ActionModule(ActionBase):
    _VALID_ARGS = frozenset(["node_name"])

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = {}
        result = super(ActionModule, self).run(tmp, task_vars)
        node_name = self._task.args.get("node_name", None)
        if node_name is None or not isinstance(node_name, string_types):
            raise AnsibleError("'node_name' must be set to a valid string node name")

        node_groups = get_node_groups_from_node_name(node_name)

        display.v("Node Name: " + node_name)
        display.v("Node groups: " + ",".join(node_groups))

        global_facts_with_tdp_prefix = [
            key for key in task_vars.keys() if key.startswith(PREFIX)
        ]
        groups = MANDATORY_GROUPS + sort_groups(global_facts_with_tdp_prefix, node_groups)
        display.v("Group order: " + str(groups))
        # Merge all tdp_vars groups
        vars = {}
        for group in groups:
            vars_from_group = task_vars.get(group, {})
            vars = merge_hash(vars, vars_from_group)

        # HostVars are more important than a group var
        vars_merged_with_task_vars = merge_hash(vars, task_vars)

        # Make merged variables available to template engine
        self._templar.available_variables = vars_merged_with_task_vars
        # Template the merged dict using ansible templating engine
        result["ansible_facts"] = {
            key: self._templar.template(vars_merged_with_task_vars[key]) for key in vars
        }
        result["changed"] = False
        return result
