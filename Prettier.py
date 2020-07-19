#!/usr/bin/env python
# coding: utf-8
#
# Prettier.py
#
# AGPLv3 License
# Created by github.com/aerobounce on 2020/07/19.
# Copyright © 2020 to Present, aerobounce. All rights reserved.
#

import html
import re
from subprocess import PIPE, Popen

import sublime
import sublime_plugin

SETTINGS_FILENAME = "Prettier.sublime-settings"
PHANTOM_STYLE = """
<style>
    div.error-arrow {
        border-top: 0.4rem solid transparent;
        border-left: 0.5rem solid color(var(--redish) blend(var(--background) 30%));
        width: 0;
        height: 0;
    }
    div.error {
        padding: 0.4rem 0 0.4rem 0.7rem;
        margin: 0 0 0.2rem;
        border-radius: 0 0.2rem 0.2rem 0.2rem;
    }
    div.error span.message {
        padding-right: 0.7rem;
    }
    div.error a {
        text-decoration: inherit;
        padding: 0.35rem 0.7rem 0.45rem 0.8rem;
        position: relative;
        bottom: 0.05rem;
        border-radius: 0 0.2rem 0.2rem 0;
        font-weight: bold;
    }
    html.dark div.error a {
        background-color: #00000018;
    }
    html.light div.error a {
        background-color: #ffffff18;
    }
</style>
"""
PHANTOM_SETS = {}


def update_phantoms(view, stderr, region):
    view_id = view.id()

    view.erase_phantoms(str(view_id))
    if view_id in PHANTOM_SETS:
        PHANTOM_SETS.pop(view_id)

    if not stderr or not "Unexpected" in stderr or not "SyntaxError" in stderr:
        return

    if not view_id in PHANTOM_SETS:
        PHANTOM_SETS[view_id] = sublime.PhantomSet(view, str(view_id))

    # Extract line and column
    digits = re.compile(r"\d+|$").findall(stderr)
    line = int(digits[0]) - 1
    column = int(digits[1]) - 1

    if region:
        line += view.rowcol(region.begin())[0]

    # Format error message
    # [error] stdin: SyntaxError: Unexpected token (23:5)
    # [error] stdin: SyntaxError: Unexpected token (23:5)

    pattern = ".*SyntaxError: "
    stderr = re.compile(pattern).sub("", stderr)
    pattern = "\\[.*"
    stderr = re.compile(pattern).sub("", stderr)

    def erase_phantom(self):
        view.erase_phantoms(str(view_id))

    phantoms = []
    point = view.text_point(line, column)
    region = sublime.Region(point, view.line(point).b)
    phantoms.append(
        sublime.Phantom(
            region,
            (
                "<body id=inline-error>"
                + PHANTOM_STYLE
                + '<div class="error-arrow"></div><div class="error">'
                + '<span class="message">'
                + html.escape(stderr, quote=False)
                + "</span>"
                + "<a href=hide>"
                + chr(0x00D7)
                + "</a></div>"
                + "</body>"
            ),
            sublime.LAYOUT_BELOW,
            on_navigate=erase_phantom,
        )
    )
    PHANTOM_SETS[view_id].update(phantoms)

    # Scroll to the syntax error point
    if sublime.load_settings(SETTINGS_FILENAME).get("scroll_to_error_point"):
        view.sel().clear()
        view.sel().add(sublime.Region(point))
        view.show_at_center(point)


def prettier(view, edit, use_selection):
    def detect_parser():
        # <flow|babel|babel-flow|babel-ts|typescript|css|less|scss|
        #  json|json5|json-stringify|graphql|markdown|mdx|vue|yaml|html|angular|lwc>
        filename = view.file_name().lower()
        ext = view.window().extract_variables()["file_extension"].lower()
        syntax = view.settings().get("syntax")

        if ext == "ts" or ext == "ts":
            return "typescript"

        if filename == "package.json" or filename == "composer.json" or ext.startswith("sublime"):
            return "json-stringify"

        if ext == "json" or syntax == "JSON":
            return "json"

        if ext == "graphql" or ext == "gql":
            return "graphql"

        if ext == "mdx":
            return "mdx"

        if ext == "md":
            return "markdown"

        if ext == "yml":
            return "yaml"

        if ext == "vue":
            return "vue"

        if ext == "js" or ext == "jsx" or ext == "mjs":
            return "babel"

        if ext == "less":
            return "less"

        if ext == "css" or ext == "scss":
            return "css"

        if ext == "html" or ext == "htm":
            return "html"

        if ext == "php":
            return "php"

        return ""


    # Load settings file
    settings = sublime.load_settings(SETTINGS_FILENAME)

    # Get bin path
    prettier_bin_path = "{} ".format(settings.get("prettier_bin_path"))

    # Get option values
    arrow_parens_value                = settings.get("arrow-parens")
    no_bracket_spacing_value          = settings.get("no-bracket-spacing")
    end_of_line_value                 = settings.get("end-of-line")
    html_whitespace_sensitivity_value = settings.get("html-whitespace-sensitivity")
    jsx_bracket_same_line_value       = settings.get("jsx-bracket-same-line")
    jsx_single_quote_value            = settings.get("jsx-single-quote")
    parser_value = detect_parser()
    print_width_value                 = settings.get("print-width")
    prose_wrap_value                  = settings.get("prose-wrap")
    quote_props_value                 = settings.get("quote-props")
    no_semi_value                     = settings.get("no-semi")
    single_quote_value                = settings.get("single-quote")
    tab_width_value                   = settings.get("tab-width")
    trailing_comma_value              = settings.get("trailing-comma")
    use_tabs_value                    = settings.get("use-tabs")
    vue_indent_script_and_style_value = settings.get("vue-indent-script-and-style")

    # Prepare options
    arrow_parens = "--arrow-parens {} ".format(arrow_parens_value)                                              if arrow_parens_value else ""
    no_bracket_spacing = "--no-bracket-spacing {} ".format(no_bracket_spacing_value)                            if no_bracket_spacing_value else ""
    end_of_line = "--end-of-line {} ".format(end_of_line_value)                                                 if end_of_line_value else ""
    html_whitespace_sensitivity = "--html-whitespace-sensitivity {} ".format(html_whitespace_sensitivity_value) if html_whitespace_sensitivity_value else ""
    jsx_bracket_same_line = "--jsx-bracket-same-line {} ".format(jsx_bracket_same_line_value)                   if jsx_bracket_same_line_value else ""
    jsx_single_quote = "--jsx-single-quote {} ".format(jsx_single_quote_value)                                  if jsx_single_quote_value else ""
    parser = "--parser {} ".format(parser_value)                                                                if parser_value else ""
    print_width = "--print-width {} ".format(print_width_value)                                                 if print_width_value else ""
    prose_wrap = "--prose-wrap {} ".format(prose_wrap_value)                                                    if prose_wrap_value else ""
    quote_props = "--quote-props {} ".format(quote_props_value)                                                 if quote_props_value else ""
    no_semi = "--no-semi {} ".format(no_semi_value)                                                             if no_semi_value else ""
    single_quote = "--single-quote {} ".format(single_quote_value)                                              if single_quote_value else ""
    tab_width = "--tab-width {} ".format(tab_width_value)                                                       if tab_width_value else ""
    trailing_comma = "--trailing-comma {} ".format(trailing_comma_value)                                        if trailing_comma_value else ""
    use_tabs = "--use-tabs {} ".format(use_tabs_value)                                                          if use_tabs_value else ""
    vue_indent_script_and_style = "--vue-indent-script-and-style {} ".format(vue_indent_script_and_style_value) if vue_indent_script_and_style_value else ""

    # Compose prettier command
    command = (
        prettier_bin_path
        + arrow_parens
        + no_bracket_spacing
        + end_of_line
        + html_whitespace_sensitivity
        + jsx_bracket_same_line
        + jsx_single_quote
        + parser
        + print_width
        + prose_wrap
        + quote_props
        + no_semi
        + single_quote
        + tab_width
        + trailing_comma
        + use_tabs
        + vue_indent_script_and_style
        + "--no-config "
        + "--no-editorconfig "
        + "--no-color"
    )

    # Format

    def format_text(target_text, selection, region):
        # Open subprocess with the command
        with Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE) as popen:
            # Write selection into stdin, then ensure the descriptor is closed
            popen.stdin.write(target_text.encode("utf-8"))
            popen.stdin.close()

            # Read stdout and stderr
            stdout = popen.stdout.read().decode("utf-8")
            stderr = popen.stderr.read().decode("utf-8")

            # Replace with result if only stderr is empty
            if not stderr:
                view.replace(edit, selection, stdout)

            # Present alert if 'prettier' not found
            if stderr and "not found" in stderr:
                sublime.error_message(
                    "Prettier - Error:\n"
                    + stderr
                    + "Specify absolute path to 'prettier' in settings"
                )
                return stderr

            # Present alert of unknown error
            if stderr and not "Unexpected" in stderr and not "SyntaxError" in stderr:
                sublime.error_message("Prettier - Error:\n" + stderr + "\n")
                return stderr

            # Update Phantoms
            update_phantoms(view, stderr, region)

            return stderr

    # Prevent needles iteration AMAP
    has_selection = any([not r.empty() for r in view.sel()])
    if (settings.get("format_selection_only") or use_selection) and has_selection:
        for region in view.sel():
            if region.empty():
                continue

            # Break at the first error
            if format_text(view.substr(region), region, region):
                break

    else:
        # Don't format entire file when use_selection is true
        if use_selection:
            return

        # Use entire region/string of view
        selection = sublime.Region(0, view.size())
        target_text = view.substr(selection)
        format_text(target_text, selection, None)


class PrettierCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        prettier(self.view, edit, False)


class PrettierSelectionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        prettier(self.view, edit, True)


class PrettierListener(sublime_plugin.ViewEventListener):
    def on_pre_save(self):
        extensions = sublime.load_settings(SETTINGS_FILENAME).get("extensions")
        file_extension = self.view.window().extract_variables()["file_extension"]

        if any(file_extension in ext for ext in extensions):
            if sublime.load_settings(SETTINGS_FILENAME).get("format_on_save"):
                self.view.run_command("prettier")

    def on_close(self):
        view_id = self.view.id()
        if view_id in PHANTOM_SETS:
            PHANTOM_SETS.pop(view_id)
