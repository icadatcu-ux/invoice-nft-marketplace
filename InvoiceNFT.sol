// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract InvoiceNFT {
    struct Invoice {
        uint256 tokenId;
        bytes32 documentHash;
        uint256 amount;          // Invoice amount in smallest unit (e.g., cents)
        uint256 dueDate;         // Unix timestamp
        address supplier;        // Original invoice holder
        address currentOwner;    // Current NFT owner
        bool isRedeemed;         // Whether invoice has been paid
        uint256 listedPrice;     // If listed for sale (0 = not listed)
        uint8 riskScore;         // 0-100, from fraud detection
        string metadata;         // JSON metadata
    }
    
    mapping(uint256 => Invoice) public invoices;
    mapping(bytes32 => uint256) public hashToTokenId;
    uint256 public nextTokenId = 1;
    
    event InvoiceMinted(
        uint256 indexed tokenId,
        bytes32 indexed documentHash,
        address indexed supplier,
        uint256 amount,
        uint256 dueDate
    );
    
    event InvoiceListed(
        uint256 indexed tokenId,
        uint256 price,
        uint256 discount
    );
    
    event InvoiceSold(
        uint256 indexed tokenId,
        address indexed from,
        address indexed to,
        uint256 price
    );
    
    event InvoiceRedeemed(
        uint256 indexed tokenId,
        address indexed redeemer,
        uint256 amount
    );
    
    // Mint invoice as NFT
    function mintInvoice(
        bytes32 _documentHash,
        uint256 _amount,
        uint256 _dueDate,
        uint8 _riskScore,
        string memory _metadata
    ) public returns (uint256) {
        require(hashToTokenId[_documentHash] == 0, "Invoice already tokenized");
        require(_amount > 0, "Amount must be positive");
        require(_dueDate > block.timestamp, "Due date must be in future");
        
        uint256 tokenId = nextTokenId++;
        
        invoices[tokenId] = Invoice({
            tokenId: tokenId,
            documentHash: _documentHash,
            amount: _amount,
            dueDate: _dueDate,
            supplier: msg.sender,
            currentOwner: msg.sender,
            isRedeemed: false,
            listedPrice: 0,
            riskScore: _riskScore,
            metadata: _metadata
        });
        
        hashToTokenId[_documentHash] = tokenId;
        
        emit InvoiceMinted(tokenId, _documentHash, msg.sender, _amount, _dueDate);
        
        return tokenId;
    }
    
    // List invoice for sale (early payment)
    function listInvoice(uint256 _tokenId, uint256 _price) public {
        Invoice storage invoice = invoices[_tokenId];
        require(invoice.tokenId != 0, "Invoice does not exist");
        require(invoice.currentOwner == msg.sender, "Not the owner");
        require(!invoice.isRedeemed, "Invoice already redeemed");
        require(_price < invoice.amount, "Price must be less than face value");
        require(_price > 0, "Price must be positive");
        
        invoice.listedPrice = _price;
        
        uint256 discount = ((invoice.amount - _price) * 10000) / invoice.amount; // basis points
        
        emit InvoiceListed(_tokenId, _price, discount);
    }
    
    // Buy invoice from marketplace
    function buyInvoice(uint256 _tokenId) public payable {
        Invoice storage invoice = invoices[_tokenId];
        require(invoice.tokenId != 0, "Invoice does not exist");
        require(!invoice.isRedeemed, "Invoice already redeemed");
        require(invoice.listedPrice > 0, "Invoice not listed");
        require(msg.value >= invoice.listedPrice, "Insufficient payment");
        require(invoice.currentOwner != msg.sender, "Cannot buy own invoice");
        
        address previousOwner = invoice.currentOwner;
        uint256 price = invoice.listedPrice;
        
        // Transfer ownership
        invoice.currentOwner = msg.sender;
        invoice.listedPrice = 0; // Unlist after purchase
        
        // Pay previous owner
        payable(previousOwner).transfer(price);
        
        // Refund excess
        if (msg.value > price) {
            payable(msg.sender).transfer(msg.value - price);
        }
        
        emit InvoiceSold(_tokenId, previousOwner, msg.sender, price);
    }
    
    // Redeem invoice (mark as paid)
    function redeemInvoice(uint256 _tokenId) public payable {
        Invoice storage invoice = invoices[_tokenId];
        require(invoice.tokenId != 0, "Invoice does not exist");
        require(!invoice.isRedeemed, "Invoice already redeemed");
        require(msg.value >= invoice.amount, "Insufficient payment");
        
        address owner = invoice.currentOwner;
        uint256 amount = invoice.amount;
        
        invoice.isRedeemed = true;
        invoice.listedPrice = 0;
        
        // Pay current owner (who gets the full amount)
        payable(owner).transfer(amount);
        
        // Refund excess
        if (msg.value > amount) {
            payable(msg.sender).transfer(msg.value - amount);
        }
        
        emit InvoiceRedeemed(_tokenId, msg.sender, amount);
    }
    
    // Cancel listing
    function cancelListing(uint256 _tokenId) public {
        Invoice storage invoice = invoices[_tokenId];
        require(invoice.tokenId != 0, "Invoice does not exist");
        require(invoice.currentOwner == msg.sender, "Not the owner");
        
        invoice.listedPrice = 0;
    }
    
    // Get invoice details
    function getInvoice(uint256 _tokenId) public view returns (
        bytes32 documentHash,
        uint256 amount,
        uint256 dueDate,
        address supplier,
        address currentOwner,
        bool isRedeemed,
        uint256 listedPrice,
        uint8 riskScore
    ) {
        Invoice memory invoice = invoices[_tokenId];
        require(invoice.tokenId != 0, "Invoice does not exist");
        
        return (
            invoice.documentHash,
            invoice.amount,
            invoice.dueDate,
            invoice.supplier,
            invoice.currentOwner,
            invoice.isRedeemed,
            invoice.listedPrice,
            invoice.riskScore
        );
    }
    
    // Calculate optimal discount based on risk and time
    function calculateRecommendedPrice(uint256 _tokenId) public view returns (uint256) {
        Invoice memory invoice = invoices[_tokenId];
        require(invoice.tokenId != 0, "Invoice does not exist");
        require(!invoice.isRedeemed, "Invoice already redeemed");
        
        // Time to maturity (in days)
        uint256 daysToMaturity = (invoice.dueDate - block.timestamp) / 86400;
        
        // Base discount: 0.1% per day
        uint256 timeDiscount = daysToMaturity * 10; // basis points
        
        // Risk premium: 0-10% based on risk score
        uint256 riskPremium = uint256(invoice.riskScore) * 10; // basis points
        
        // Total discount
        uint256 totalDiscount = timeDiscount + riskPremium;
        if (totalDiscount > 5000) totalDiscount = 5000; // Cap at 50%
        
        // Calculate price
        uint256 recommendedPrice = invoice.amount - (invoice.amount * totalDiscount / 10000);
        
        return recommendedPrice;
    }
}
