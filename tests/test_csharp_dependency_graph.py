"""C# dependency graph: per-file edges, global graph, call chains, ambiguity (issue #4)."""

from __future__ import annotations

import textwrap

from token_savior.csharp_annotator import annotate_csharp
from token_savior.project_indexer import ProjectIndexer
from token_savior.query_api import ProjectQueryEngine, create_project_query_functions

REPOSITORY_INTERFACE = """\
namespace Notifications;

public interface INotificationRepository
{
    Task<long> GetMaxSequenceIdAsync(CancellationToken ct);
}
"""

REPOSITORY_IMPL = """\
namespace Notifications;

public sealed class SqliteNotificationRepository : INotificationRepository
{
    public async Task<long> GetMaxSequenceIdAsync(CancellationToken ct)
    {
        using var connection = await OpenAsync(ct);
        return 0;
    }

    private Task<object> OpenAsync(CancellationToken ct)
    {
        return Task.FromResult(new object());
    }
}
"""

WORKER_FIELD = """\
namespace Notifications;

public sealed class NotificationWorker
{
    private readonly INotificationRepository _repository;

    public NotificationWorker(INotificationRepository repository)
    {
        _repository = repository;
    }

    public async Task ExecuteAsync(CancellationToken ct)
    {
        await DiscoverAsync(ct);
    }

    private async Task DiscoverAsync(CancellationToken ct)
    {
        var max = await _repository.GetMaxSequenceIdAsync(ct);
    }
}
"""

WORKER_PRIMARY_CTOR = """\
namespace Notifications;

public sealed class NotificationWorker(INotificationRepository repository)
{
    public async Task DiscoverAsync(CancellationToken ct)
    {
        var max = await repository.GetMaxSequenceIdAsync(ct);
    }
}
"""


def _write(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content))


def _project(root, worker: str = WORKER_FIELD):
    root.mkdir()
    _write(root / "INotificationRepository.cs", REPOSITORY_INTERFACE)
    _write(root / "SqliteNotificationRepository.cs", REPOSITORY_IMPL)
    _write(root / "NotificationWorker.cs", worker)
    idx = ProjectIndexer(str(root)).index()
    return idx, create_project_query_functions(idx)


class TestPerFileGraph:
    def test_same_class_call_edge(self):
        graph = annotate_csharp(WORKER_FIELD).dependency_graph
        assert "NotificationWorker.DiscoverAsync" in graph["NotificationWorker.ExecuteAsync"]

    def test_field_typed_call_edge(self):
        graph = annotate_csharp(WORKER_FIELD).dependency_graph
        deps = graph["NotificationWorker.DiscoverAsync"]
        assert "INotificationRepository.GetMaxSequenceIdAsync" in deps

    def test_primary_constructor_parameter_call_edge(self):
        graph = annotate_csharp(WORKER_PRIMARY_CTOR).dependency_graph
        deps = graph["NotificationWorker.DiscoverAsync"]
        assert "INotificationRepository.GetMaxSequenceIdAsync" in deps

    def test_object_creation_edge(self):
        source = """\
        public class Factory
        {
            public Widget Make()
            {
                return new Widget();
            }
        }
        """
        graph = annotate_csharp(textwrap.dedent(source)).dependency_graph
        assert {"Widget", "Widget.Widget"} <= set(graph["Factory.Make"])

    def test_local_variable_and_static_call_edges(self):
        source = """\
        public class Job
        {
            public void Run()
            {
                var helper = new Helper();
                helper.Go();
                Registry.Register(this);
            }
        }
        """
        deps = annotate_csharp(textwrap.dedent(source)).dependency_graph["Job.Run"]
        assert "Helper.Go" in deps
        assert "Registry.Register" in deps

    def test_base_class_edge_and_inherited_call(self):
        source = """\
        public class Child : Parent
        {
            public void Work()
            {
                Setup();
                base.Work();
            }
        }
        """
        graph = annotate_csharp(textwrap.dedent(source)).dependency_graph
        assert "Parent" in graph["Child"]
        assert "Parent.Setup" in graph["Child.Work"]
        assert "Parent.Work" in graph["Child.Work"]
        assert "Child.Work" not in graph["Child.Work"]

    def test_comments_and_strings_create_no_edges(self):
        source = """\
        public class Quiet
        {
            public void Run()
            {
                // Helper.Go();
                var text = "Helper.Go() and new Helper()";
                /* Other.Thing(); */
            }
        }
        """
        deps = annotate_csharp(textwrap.dedent(source)).dependency_graph["Quiet.Run"]
        assert not any(dep.startswith(("Helper", "Other")) for dep in deps)


class TestGlobalGraph:
    def test_worker_depends_on_interface_and_implementation(self, tmp_path):
        idx, _ = _project(tmp_path / "cs")
        deps = idx.global_dependency_graph["NotificationWorker.DiscoverAsync"]
        assert "INotificationRepository.GetMaxSequenceIdAsync" in deps
        assert "SqliteNotificationRepository.GetMaxSequenceIdAsync" in deps

    def test_unknown_external_names_are_dropped(self, tmp_path):
        idx, _ = _project(tmp_path / "cs")
        deps = idx.global_dependency_graph["SqliteNotificationRepository.OpenAsync"]
        assert not any(dep.startswith(("Task", "CancellationToken")) for dep in deps)

    def test_get_call_chain_through_interface_dispatch(self, tmp_path):
        _, funcs = _project(tmp_path / "cs")
        result = funcs["get_call_chain"](
            "NotificationWorker.DiscoverAsync",
            "SqliteNotificationRepository.OpenAsync",
        )
        assert "chain" in result, result
        names = [step["name"] for step in result["chain"]]
        assert names[0] == "NotificationWorker.DiscoverAsync"
        assert names[-1] == "SqliteNotificationRepository.OpenAsync"

    def test_get_call_chain_with_primary_constructor_worker(self, tmp_path):
        _, funcs = _project(tmp_path / "cs", WORKER_PRIMARY_CTOR)
        result = funcs["get_call_chain"](
            "NotificationWorker.DiscoverAsync",
            "SqliteNotificationRepository.OpenAsync",
        )
        assert "chain" in result, result

    def test_get_dependents_finds_callers(self, tmp_path):
        idx, _ = _project(tmp_path / "cs")
        dependents = idx.reverse_dependency_graph["SqliteNotificationRepository.OpenAsync"]
        assert "SqliteNotificationRepository.GetMaxSequenceIdAsync" in dependents


class TestAmbiguousInterfaceMethod:
    def test_bare_name_lists_both_candidates(self, tmp_path):
        _, funcs = _project(tmp_path / "cs")
        info = funcs["find_symbol"]("GetMaxSequenceIdAsync")
        assert "ambiguous" in info["error"]
        names = {c["name"] for c in info["candidates"]}
        assert names == {
            "INotificationRepository.GetMaxSequenceIdAsync",
            "SqliteNotificationRepository.GetMaxSequenceIdAsync",
        }
        assert all(c["file"] for c in info["candidates"])

    def test_qualified_name_resolves(self, tmp_path):
        _, funcs = _project(tmp_path / "cs")
        info = funcs["find_symbol"]("SqliteNotificationRepository.GetMaxSequenceIdAsync")
        assert "error" not in info
        assert info["name"] == "SqliteNotificationRepository.GetMaxSequenceIdAsync"


STORE_WITH_OWN_OPEN = """\
namespace Notifications;

public sealed class SqliteDeliveryStore
{
    private async Task<object> OpenAsync()
    {
        return new object();
    }

    public async Task CaptureAsync()
    {
        await using var connection = await OpenAsync();
    }
}
"""

WORKER_USING_STORE = """\
namespace Notifications;

public sealed class NotificationWorker
{
    private readonly SqliteDeliveryStore _store = new SqliteDeliveryStore();

    public async Task DiscoverAsync()
    {
        await _store.CaptureAsync();
    }
}
"""


class TestSameNameMethodsOfUnrelatedClasses:
    """Issue #9: two classes each own a private OpenAsync; they must not be confused."""

    def _two_openers(self, root):
        root.mkdir()
        _write(root / "SqliteNotificationRepository.cs", REPOSITORY_IMPL)
        _write(root / "SqliteDeliveryStore.cs", STORE_WITH_OWN_OPEN)
        _write(root / "NotificationWorker.cs", WORKER_USING_STORE)
        idx = ProjectIndexer(str(root)).index()
        return idx, create_project_query_functions(idx)

    def test_unqualified_call_resolves_to_the_enclosing_class(self, tmp_path):
        idx, _ = self._two_openers(tmp_path / "cs")
        deps = idx.global_dependency_graph["SqliteDeliveryStore.CaptureAsync"]
        assert "SqliteDeliveryStore.OpenAsync" in deps
        assert "SqliteNotificationRepository.OpenAsync" not in deps

    def test_no_call_chain_through_a_same_name_private_helper(self, tmp_path):
        _, funcs = self._two_openers(tmp_path / "cs")
        result = funcs["get_call_chain"](
            "NotificationWorker.DiscoverAsync",
            "SqliteNotificationRepository.OpenAsync",
        )
        assert "chain" not in result, result
        assert "no path" in result["error"]

    def test_chain_to_the_class_that_really_owns_the_call_is_kept(self, tmp_path):
        _, funcs = self._two_openers(tmp_path / "cs")
        result = funcs["get_call_chain"](
            "NotificationWorker.DiscoverAsync", "SqliteDeliveryStore.OpenAsync"
        )
        names = [step["name"] for step in result["chain"]]
        assert names[0] == "NotificationWorker.DiscoverAsync"
        assert names[-1] == "SqliteDeliveryStore.OpenAsync"

    def test_target_names_do_not_include_sibling_methods(self, tmp_path):
        idx, _ = self._two_openers(tmp_path / "cs")
        engine = ProjectQueryEngine(idx)
        names = engine._get_graph_target_names("SqliteNotificationRepository.OpenAsync")
        assert "SqliteNotificationRepository.OpenAsync" in names
        assert "SqliteNotificationRepository.GetMaxSequenceIdAsync" not in names
        assert "OpenAsync" not in names
