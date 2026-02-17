contract.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract InvoiceRegistry {
    struct Invoice {
        uint256 timestamp;
        address registrar;
        string metadata;
        bool exists;
    }
    
    mapping(bytes32 => Invoice) public invoices;
    
    event InvoiceRegistered(
        bytes32 indexed invoiceHash,
        address indexed registrar,
        uint256 timestamp,
        string metadata
    );
    
    function registerInvoice(bytes32 _invoiceHash, string memory _metadata) public {
        require(!invoices[_invoiceHash].exists, "Invoice already registered");
        
        invoices[_invoiceHash] = Invoice({
            timestamp: block.timestamp,
            registrar: msg.sender,
            metadata: _metadata,
            exists: true
        });
        
        emit InvoiceRegistered(_invoiceHash, msg.sender, block.timestamp, _metadata);
    }
    
    function getInvoice(bytes32 _invoiceHash) public view returns (
        uint256 timestamp,
        address registrar,
        string memory metadata
    ) {
        require(invoices[_invoiceHash].exists, "Invoice not found");
        Invoice memory inv = invoices[_invoiceHash];
        return (inv.timestamp, inv.registrar, inv.metadata);
    }
    
    function verifyInvoice(bytes32 _invoiceHash) public view returns (bool) {
        return invoices[_invoiceHash].exists;
    }
}
