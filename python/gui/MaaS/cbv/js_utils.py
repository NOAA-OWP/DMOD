def start_end_time_validation(start_time_id: str, end_time_id: str) -> str:
    """Applies validity testing to start and end time input DOM elements of type`datetime-local`. If
    start time is after end time or end time is prior to start, an input validity message is tagged
    on the `start_time_id` element.
    """
    return f"""((start_time_id, end_time_id) => {{

                let start_time_el = document.getElementById(start_time_id);
                let end_time_el = document.getElementById(end_time_id);

                if (start_time_el == null){{
                    console.error(`invalid start_time_id: ${{start_time_id}}`)
                    return;
                }}

                if (end_time_el == null){{
                    console.error(`invalid end_time_id: ${{end_time_id}}`)
                    return;
                }}

                if (start_time_el.value === '' || end_time_el.value === ''){{
                    // missing time value
                    return;
                }}

                const start_time = new Date(start_time_el.value);
                const end_time = new Date(end_time_el.value);

                if (start_time.getTime() > end_time.getTime()){{
                    start_time_el.setCustomValidity('Start time after end time');
                    return;
                }}

                // reset
                start_time_el.setCustomValidity('');
        }})('{start_time_id}', '{end_time_id}')"""
