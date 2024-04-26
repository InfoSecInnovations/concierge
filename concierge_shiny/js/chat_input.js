console.log("js init")

$('.chat-text-input input[type="text"]').on('keydown', function(ev) {
    if (ev.code !== "Enter") { return; }
    // Get the "enter" input id in the module namespace
    const enterIdMod = ev.target.closest('.chat-text-input').dataset.enterId;
    console.log(enterIdMod)
    // Report the text value at input.enter()
    Shiny.setInputValue(enterIdMod, ev.target.value, {priority: "event"});
});