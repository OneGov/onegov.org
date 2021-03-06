/*
    Provides an easy way to toggle detail information with a button.

    Buttons which should toggle a content block need a data-toggle attribute,w
    which contains the selector of the content block which needs to be toggled.

    The initial state of the toggle is defined by the content block. If it
    is hidden (using style="display: none;"), the initial state is "untoggled",
    otherwise the state is "toggled".

    The state is stored as a class on the button.

    Using the style attribute as the initial style forces us to render the
    site correctly on the first pass, without having to change the visibility
    of elements through javascript leading to an expensive re-render.

    Additionally the toggled/untoggled class may be set on the button as well,
    though it will be corrected if it is wrong (so the ultimate source of
    truth is the style element of the target block).

    Example of an initially untoggled element:

        <div data-toggle="#details">Show Details</div>
        <div id="#details" style="display: none;"></div>

    Example of an initially toggled element:

        <div data-toggle="#details" class="toggled">Show Details</div>
        <div id="#details"></div>

    You can have an alternative text in the toggled/untoggled state by
    providing an alt text. The alt text is used if the button changes from
    the initial state to the next:

        <div data-toggle="#details" data-alt-text="Hide">Show</div>
        <div id="#details"></div>
*/

var isToggled = function(target) {
    return target.css('display') !== 'none' && true || false;
};

var ensureToggled = function(button, target, toggled) {
    button.toggleClass('toggled', toggled);

    if (toggled) {
        button.attr('aria-pressed', 'true');
    } else {
        button.attr('aria-pressed', 'false');
    }

    if (typeof button.attr('data-toggle-initialised') !== 'undefined') {
        if (typeof button.attr('data-original-text') !== 'undefined') {
            button.attr('data-alt-text', button.text());
            button.text(button.attr('data-original-text'));
            button.removeAttr('data-original-text');
        }
        else if (typeof button.attr('data-alt-text') !== 'undefined') {
            button.attr('data-original-text', button.text());
            button.text(button.attr('data-alt-text'));
            button.removeAttr('data-alt-text');
        }
    }

    button.attr('data-toggle-initialised', true);

    if (target.is(':visible') !== toggled) {
        if (toggled) {
            target.show();
        } else {
            target.hide();
        }
    }
};

var clickToggled = function(e) {
    var button = $(this);
    var target = $(button.data('toggle'));

    ensureToggled(button, target, !isToggled(target));

    e.preventDefault();
    return false;
};

var ToggleButton = function(button, toggled) {
    var target = $(button.data('toggle'));
    var toggle = null;

    if (_.isUndefined(toggled)) {
        toggle = isToggled(target);
    } else {
        toggle = toggled;
    }

    button.attr('role', 'button');

    ensureToggled(button, target, toggle);
    button.click(clickToggled);
};

jQuery.fn.toggleButton = function(toggled) {
    return this.each(function() {
        var button = $(this);

        // do not unduly block the main thread here
        setTimeout(function() {
            ToggleButton(button, toggled);
        }, 0);
    });
};
