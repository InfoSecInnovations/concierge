$('.text-input-enter input[type="text"]').on('keydown', function(ev) {
    if (ev.code !== "Enter") { return; }
    // Get the "enter" input id in the module namespace
    const enterIdMod = ev.target.closest('.text-input-enter').dataset.enterId;
    // Report the text value at input.enter()
    Shiny.setInputValue(enterIdMod, ev.target.value, {priority: "event"});
});