def left_slider_moved(self, val):

    if self.markers_locked:
        if self.slider_right.val != val:
            self.slider_right.set_val(val)
            self.update_right_cursor(val)

    self.markers[0]["index"] = int(val)

def right_slider_moved(self, val):

    if self.markers_locked:
        if self.slider_left.val != val:
            self.slider_left.set_val(val)
            self.update_cursor(val)

    self.markers[1]["index"] = int(val)

def left_slider_moved_2(self, val):

    if self.markers_locked:
        if self.slider_right_2.val != val:
            self.slider_right_2.set_val(val)
            self.update_right_cursor_2(val)

    self.markers[0]["index_2"] = int(val)

def right_slider_moved_2(self, val):

    if self.markers_locked:
        if self.slider_left_2.val != val:
            self.slider_left_2.set_val(val)
            self.update_cursor_2(val)

    self.markers[1]["index_2"] = int(val)