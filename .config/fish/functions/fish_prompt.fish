function fish_prompt
    # 1. Print the current directory path cleanly in cyan
    set_color cyan
    printf '%s ' (prompt_pwd)

    # 2. Dynamic Wallpaper Color Matching
    # Grabs color2 directly from your active Pywal configuration sequence
    if set -q color2
        set_color $color2
    else if set -q color1
        set_color $color1
    else
        # Fallback to a warm orange/brown matching your backdrop
        set_color d79921
    end

    # 3. Direct Unicode escape code for the Arch Logo (Won't get lost or dropped)
    printf '\uF303 '

    # 4. Print your arrow prompt character
    set_color normal
    printf '❯ '
end
