function wine32 --wraps='env WINEPREFIX=~/.wine32 prime-run wine' --description 'alias wine32=env WINEPREFIX=~/.wine32 prime-run wine'
    env WINEPREFIX=~/.wine32 prime-run wine $argv
end
