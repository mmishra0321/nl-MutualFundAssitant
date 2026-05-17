"""Run: PYTHONPATH=phases/corpus python -m ms02_corpus.p1_5_pipeline [options] [raw_dir] [intermediate_dir] [normalized_dir]"""

from ms02_corpus.p1_5_pipeline.pipeline import main

if __name__ == "__main__":
    raise SystemExit(main())
