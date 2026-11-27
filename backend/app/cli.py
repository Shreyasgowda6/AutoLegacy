"""Terminal interface: python -m app.cli [index | ask QUESTION]."""
import argparse

from app.config import load_settings
from app.ollama import OllamaError
from app.rag import RAG
from app.schemas import ChatRequest


def show(engine, question):
    print('Searching knowledge...', flush=True)
    result = engine.ask(ChatRequest(question=question))
    print('\n' + result.answer)
    for source in result.sources:
        print(f'  Source: {source.id} - {source.problem} (distance {source.distance:.3f})')
    print()


def main():
    parser = argparse.ArgumentParser(description='Ask questions using the synthetic JSON knowledge base and local Ollama.')
    parser.add_argument('command', nargs='?', choices=['index', 'ask'])
    parser.add_argument('question', nargs='?')
    args = parser.parse_args()
    engine = RAG(load_settings())
    try:
        if args.command == 'index':
            print('Indexing JSON knowledge...', flush=True)
            records, _ = engine.index(force=True)
            print(f'Indexed {len(records)} JSON knowledge records.')
        elif args.command == 'ask':
            if not args.question:
                parser.error('Provide a question: python -m app.cli ask "your question"')
            show(engine, args.question)
        else:
            print('AutoLegacy demo RAG - synthetic knowledge, local Ollama. Type exit to quit.')
            while True:
                question = input('\nYou: ').strip()
                if question.lower() in {'exit', 'quit'}:
                    break
                if question:
                    try:
                        show(engine, question)
                    except (OllamaError, OSError, ValueError) as exc:
                        print(f'Error: {exc}')
    except (EOFError, KeyboardInterrupt):
        print('\nStopped.')
    except (OllamaError, OSError, ValueError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
