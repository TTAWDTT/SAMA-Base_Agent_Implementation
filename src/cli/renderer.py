# ==============================================================================
# 输出渲染
# ==============================================================================

from __future__ import annotations


class OutputRenderer:
    def __init__(self, session) -> None:
        self._session = session

    def render_response(self, response) -> str:
        session = self._session
        read_files, write_files = session._collect_file_activity(response.steps)
        raw_text = response.final_answer or ""
        explicit_paths = []
        if raw_text.strip():
            output_text, explicit_paths = session._split_output_path_lines(raw_text)
        else:
            output_text = session._get_empty_response_text()

        displayed_reads = []
        displayed_writes = []
        known_keys = set(session._live_file_paths)
        for path in read_files:
            key = session._normalize_path_key(path)
            if key in known_keys:
                continue
            if session.show_steps:
                displayed_reads.append(path)
            known_keys.add(key)
        for path in write_files:
            key = session._normalize_path_key(path)
            if key in known_keys:
                continue
            displayed_writes.append(path)
            known_keys.add(key)

        if displayed_reads or displayed_writes:
            print()
            session._render_file_activity(displayed_reads, displayed_writes)
        if session._frame_enabled:
            print()
            session._render_output_frame(output_text)
        else:
            print(session._style("\nassistant:", "bold"))
            if session._stream_enabled:
                session._stream_print(output_text)
            else:
                print(output_text)

        session._render_final_file_mentions(
            output_text,
            displayed_reads,
            displayed_writes,
            explicit_paths,
            known_keys
        )

        if session.show_steps:
            status_text = "ok" if response.success else "fail"
            meta_parts = [
                f"status={status_text}",
                f"iter={response.total_iterations}",
                f"time={response.execution_time:.2f}s"
            ]
            tool_summary = session._summarize_tools(response.steps)
            if tool_summary:
                meta_parts.append(f"tools={tool_summary}")

            print(session._style("[" + " | ".join(meta_parts) + "]", "dim"))
            if not response.success and response.error_message:
                print(session._style(f"[error] {response.error_message}", "error"))

        if session._workflow_enabled:
            session._render_workflow(response)

        return output_text
