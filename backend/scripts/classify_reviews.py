"""Reproducible local sentiment and topic jobs; no review text leaves this machine."""
import argparse
import json
from pathlib import Path
from backend.app.config import Settings,PROJECT_ROOT
from backend.app.services.analysis import run_analysis
from backend.app.services.nlp import MODEL_ID,MODEL_REVISION,load_classifier

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=['sentiment','topics'])
    parser.add_argument('--limit',type=int)
    parser.add_argument('--batch-size',type=int,default=16)
    parser.add_argument('--revision',default=MODEL_REVISION)
    parser.add_argument('--device',choices=['auto','cpu','mps'],default='auto')
    args=parser.parse_args()
    if args.batch_size<1 or (args.limit is not None and args.limit<1): parser.error('Positive batch-size/limit required')
    predictor=None;revision=args.revision;device=None
    if args.kind=='sentiment':
        if not revision:
            from huggingface_hub import HfApi
            revision=HfApi().model_info(MODEL_ID).sha
        print(f'Loading {MODEL_ID}@{revision}',flush=True)
        predictor,device=load_classifier(MODEL_ID,revision,str(PROJECT_ROOT/'backend/data/models'),args.device,args.batch_size)
        print(f'Inference device: {device}',flush=True)
    result=run_analysis(Settings.from_env().database_path,args.kind,predict=predictor,model_id=MODEL_ID if predictor else None,revision=revision if predictor else None,limit=args.limit,batch_size=args.batch_size,report_dir=PROJECT_ROOT/'backend/data/analysis')
    result['device']=device
    (PROJECT_ROOT/'backend/data/analysis'/f"{result['run_id']}.json").write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
