;; Vague implementation of needed code to invoke GNUS from reportbug
;; by Tollef Fog Heen
(require 'gnus-load)

(defun tfheen-set-header (header value)
  "Insert a string at the beginning of a header."
  (message-narrow-to-head)
  (goto-char (point-min))
  (search-forward (format "%s: " header) (point-max) t)
  (insert value)
  (widen))

(defun tfheen-reportbug-insert-template ()
  (interactive)
  (require 'gnus)
  (find-file (getenv "REPORTBUG"))
  (let ((subject (message-fetch-field "Subject"))
        (toaddr (or (message-fetch-field "To") "submit@bugs.debian.org")))
    (gnus-narrow-to-body)
    (let ((body (or (buffer-string) "")))
      (gnus-summary-mail-other-window)
      (tfheen-set-header "Subject" subject)
      (tfheen-set-header "To" toaddr)
      (gnus-narrow-to-body)
      (insert body)
      (widen)))
  (kill-buffer (find-buffer-visiting (getenv "REPORTBUG"))))
