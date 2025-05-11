#\!/bin/bash
rm -rf temp_container
mkdir -p temp_container
docker run -v $HOME/.config/rmapi:/home/app/.config/rmapi -v $(pwd)/temp_container:/temp --rm --entrypoint /bin/sh rmapi -c "cd /temp && rmapi get \"/Personal/Side Projects/Remarkable/Docs/InkLink_Current_Architecture\" ."
