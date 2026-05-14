"""
Moodle Monitor - Entry point principal

Uso:
    python main.py                    # Inicia o monitor com config padrão
    python main.py --config custom.yaml
    python main.py --once             # Executa um único ciclo e encerra
    python main.py --validate-config  # Valida a configuração e encerra
"""

import argparse
import asyncio
import sys

from src.config.settings import load_config, validate_config
from src.monitor.engine import MonitorEngine


async def async_main(args: argparse.Namespace) -> int:
    config = load_config(args.config)

    if args.validate_config:
        errors = validate_config(config)
        if errors:
            for e in errors:
                print(f"ERRO: {e}")
            return 1
        print("Configuração válida.")
        return 0

    engine = MonitorEngine(config)
    try:
        await engine.initialize()

        if args.once:
            await engine.run_single_cycle()
        else:
            await engine.run_forever()

        return 0
    except KeyboardInterrupt:
        print("\nMonitor interrompido pelo usuário.")
        return 0
    except Exception as e:
        print(f"ERRO FATAL: {e}", file=sys.stderr)
        return 1
    finally:
        await engine.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Moodle Monitor")
    parser.add_argument("--config", default="config.yaml",
                        help="Caminho do arquivo de configuração")
    parser.add_argument("--once", action="store_true",
                        help="Executa um único ciclo de monitoramento")
    parser.add_argument("--validate-config", action="store_true",
                        help="Valida a configuração e encerra")

    args = parser.parse_args()
    exit_code = asyncio.run(async_main(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
