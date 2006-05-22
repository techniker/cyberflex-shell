import TLV_utils
from generic_card import *

class ISO_7816_4_Card(Card):
    APDU_SELECT_FILE = C_APDU("\x00\xa4\x00\x00")
    APDU_READ_BINARY = C_APDU("\x00\xb0\x00\x00\x00")
    DRIVER_NAME = "ISO 7816-4"
    FID_MF = "\x3f\x00"
    
##    def can_handle(cls, card):
##        return True
##    can_handle = classmethod(can_handle)

    def select_file(self, p1, p2, fid):
        result = self.send_apdu(
            C_APDU(self.APDU_SELECT_FILE,
            p1 = p1, p2 = p2,
            data = fid, le = 0) )
        return result
    
    def change_dir(self, fid = None):
        "Change to a child DF. Alternatively, change to MF if fid is None."
        if fid is None:
            return self.select_file(0x00, 0x00, "")
        else:
            return self.select_file(0x01, 0x00, fid)
    
    def cmd_cd(self, dir = None):
        "Change into a DF, or into the MF if no dir is given"
        
        if dir is None:
            result = self.change_dir()
        else:
            fid = binascii.a2b_hex("".join(dir.split()))
            result = self.change_dir(fid)
        
        if len(result.data) > 0:
            print utils.hexdump(result.data)
            print TLV_utils.decode(result.data)
    
    def open_file(self, fid):
        "Open an EF under the current DF"
        return self.select_file(0x02, 0x00, fid)
    
    def cmd_open(self, file):
        "Open a file"
        fid = binascii.a2b_hex("".join(file.split()))
        
        result = self.open_file(fid)
        if len(result.data) > 0:
            print utils.hexdump(result.data)
            print TLV_utils.decode(result.data)

    def read_binary_file(self, offset = 0):
        """Read from the currently selected EF.
        Repeat calls to READ BINARY as necessary to get the whole EF."""
        
        if offset >= 1<<15:
            raise ValueError, "offset is limited to 15 bits"
        contents = ""
        had_one = False
        
        while True:
            command = C_APDU(self.APDU_READ_BINARY, p1 = offset >> 8, p2 = (offset & 0xff))
            result = self.send_apdu(command)
            if len(result.data) > 0:
                contents = contents + result.data
                offset = offset + len(result.data)
            
            if result.sw != self.SW_OK:
                break
            else:
                had_one = True
        
        if had_one: ## If there was at least one successful pass, ignore any error SW. It probably only means "end of file"
            self.sw_changed = False
        
        return contents
    
    def cmd_cat(self):
        "Print a hexdump of the currently selected file (e.g. consecutive READ BINARY)"
        contents = self.read_binary_file()
        self.last_result = R_APDU(contents + self.last_sw)
        print utils.hexdump(contents)
    
    def cmd_selectfile(self, p1, p2, fid):
        """Select a file on the card."""
        
        p1 = binascii.a2b_hex("".join(p1.split()))
        p2 = binascii.a2b_hex("".join(p2.split()))
        fid = binascii.a2b_hex("".join(fid.split()))
        
        result = self.select_file(p1, p2, fid)
        if len(result.data) > 0:
            print utils.hexdump(result.data)
            print TLV_utils.decode(result.data)
    
    ATRS = list(Card.ATRS)
    ATRS.extend( [
            (".*", None),   ## For now we accept any card
        ] )
    
    COMMANDS = dict(Card.COMMANDS)
    COMMANDS.update( {
        "select_file": cmd_selectfile,
        "cd": cmd_cd,
        "cat": cmd_cat,
        "open": cmd_open,
        } )

    STATUS_WORDS = dict(Card.STATUS_WORDS)
    STATUS_WORDS.update( {
        "62??": "Warning, State of non-volatile memory unchanged",
        "63??": "Warning, State of non-volatile memory changed",
        "64??": "Error, State of non-volatile memory unchanged",
        "65??": "Error, State of non-volatile memory changed",
        "66??": "Reserved for security-related issues",
        "6700": "Wrong length",
        "68??": "Functions in CLA not supported",
        "69??": "Command not allowed",
        "6A??": "Wrong parameter(s) P1-P2",
        "6B00": "Wrong parameter(s) P1-P2",
        "6D00": "Instruction code not supported or invalid",
        "6E00": "Class not supported",
        "6F00": "No precise diagnosis",
        
        "6200": "Warning, State of non-volatile memory unchanged, No information given",
        "6281": "Warning, State of non-volatile memory unchanged, Part of returned data may be corrupted",
        "6282": "Warning, State of non-volatile memory unchanged, End of file/record reached before reading Le bytes",
        "6283": "Warning, State of non-volatile memory unchanged, Selected file invalidated",
        "6284": "Warning, State of non-volatile memory unchanged, FCI not formatted according to ISO-7816-4 5.1.5",
        
        "6300": "Warning, State of non-volatile memory changed, No information given",
        "6381": "Warning, State of non-volatile memory changed, File filled up by the last write",
        "63C?": lambda SW1,SW2: "Warning, State of non-volatile memory changed, Counter provided by '%i'" % (SW2%16),
        
        "6500": "Error, State of non-volatile memory changed, No information given",
        "6581": "Error, State of non-volatile memory changed, Memory failure",
        
        "6800": "Functions in CLA not supported, No information given",
        "6881": "Functions in CLA not supported, Logical channel not supported",
        "6882": "Functions in CLA not supported, Secure messaging not supported",
        
        "6900": "Command not allowed, No information given",
        "6981": "Command not allowed, Command incompatible with file structure",
        "6982": "Command not allowed, Security status not satisfied",
        "6983": "Command not allowed, Authentication method blocked",
        "6984": "Command not allowed, Referenced data invalidated",
        "6985": "Command not allowed, Conditions of use not satisfied",
        "6986": "Command not allowed, Command not allowed (no current EF)",
        "6987": "Command not allowed, Expected SM data objects missing",
        "6988": "Command not allowed, SM data objects incorrect",
        
        "6A00": "Wrong parameter(s) P1-P2, No information given",
        "6A80": "Wrong parameter(s) P1-P2, Incorrect parameters in the data field",
        "6A81": "Wrong parameter(s) P1-P2, Function not supported",
        "6A82": "Wrong parameter(s) P1-P2, File not found",
        "6A83": "Wrong parameter(s) P1-P2, Record not found",
        "6A84": "Wrong parameter(s) P1-P2, Not enough memory space in the file",
        "6A85": "Wrong parameter(s) P1-P2, Lc inconsistent with TLV structure",
        "6A86": "Wrong parameter(s) P1-P2, Incorrect parameters P1-P2",
        "6A87": "Wrong parameter(s) P1-P2, Lc inconsistent with P1-P2",
        "6A88": "Wrong parameter(s) P1-P2, Referenced data not found",
    } )
