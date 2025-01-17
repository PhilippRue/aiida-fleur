"""
Module with utitlies for the CLI.

The echo_process_results and launch_process routines have been copied from
aiida-common-workflows repository found under cli utils
"""
import click


def echo_process_results(node):
    """Display a formatted table of the outputs registered for the given process node.

    :param node: the `ProcessNode` of a terminated process.
    """
    from aiida.common.links import LinkType

    class_name = node.process_class.__name__
    outputs = node.base.links.get_outgoing(link_type=(LinkType.CREATE, LinkType.RETURN)).all()

    if node.is_finished and node.exit_message:
        state = f'{node.process_state.value} [{node.exit_status}] `{node.exit_message}`'
    elif node.is_finished:
        state = f'{node.process_state.value} [{node.exit_status}]'
    else:
        state = node.process_state.value

    click.echo(f'{class_name}<{node.pk}> terminated with state: {state}')

    if not outputs:
        click.echo(f'{class_name}<{node.pk}> registered no outputs')
        return

    click.echo(f"\n{'Output link':25s} Node pk and type")
    click.echo(f"{'-' * 60}")

    for triple in sorted(outputs, key=lambda triple: triple.link_label):
        click.echo(f'{triple.link_label:25s} {triple.node.__class__.__name__}<{triple.node.pk}> ')


def launch_process(process, daemon, **inputs):
    """Launch a process with the given inputs.

    If not sent to the daemon, the results will be displayed after the calculation finishes.

    :param process: the process class or process builder.
    :param daemon: boolean, if True will submit to the daemon instead of running in current interpreter.
    :param inputs: inputs for the process if the process is not already a fully prepared builder.
    """
    from aiida.engine import launch, Process, ProcessBuilder

    if isinstance(process, ProcessBuilder):
        process_name = process.process_class.__name__
    elif issubclass(process, Process):
        process_name = process.__name__
    else:
        raise TypeError(f'invalid type for process: {process}')

    if daemon:
        node = launch.submit(process, **inputs)
        click.echo(f'Submitted {process_name}<{node.pk}> to the daemon')
    else:
        click.echo(f'Running a {process_name}...')
        _, node = launch.run_get_node(process, **inputs)
        echo_process_results(node)

    return node.pk    
