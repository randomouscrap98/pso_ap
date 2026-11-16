from worlds.LauncherComponents import Component, Type, components, launch


def run_client(*args: str) -> None:
    # Lazy import: keeps generation/launcher startup light (and kivy-free).
    from .client.launch import launch_client

    launch(launch_client, name="PSOBB Client", args=args)


components.append(
    Component(
        "PSOBB Client",
        func=run_client,
        game_name="Phantasy Star Online Blue Burst",
        component_type=Type.CLIENT,
        supports_uri=True,
    )
)
