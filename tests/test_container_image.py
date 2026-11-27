from pathlib import Path


def test_container_refreshes_os_security_packages_before_dropping_privileges():
    dockerfile = "\n".join(
        line.rstrip()
        for line in (Path(__file__).parents[1] / "Dockerfile").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    instructions = [
        line.split(maxsplit=1) for line in dockerfile.replace("\\\n", "").splitlines()
    ]
    instructions = [
        (opcode.upper(), " ".join(arguments.split()))
        for opcode, arguments in instructions
    ]

    assert ("USER", "app") in instructions
    before_user = instructions[: instructions.index(("USER", "app"))]
    expected_commands = [
        "apt-get update",
        "apt-get upgrade -y",
        "rm -rf /var/lib/apt/lists/*",
    ]
    assert any(
        [command.strip() for command in arguments.split("&&", 3)[:3]]
        == expected_commands
        for opcode, arguments in before_user
        if opcode == "RUN"
    ), "Expected apt-get update, upgrade and cleanup in one RUN before USER app"
