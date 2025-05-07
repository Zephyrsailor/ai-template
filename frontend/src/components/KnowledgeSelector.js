import React, { useState, useEffect, useRef } from 'react';
import styled from 'styled-components';
import { FaSearch, FaCheck, FaBook } from 'react-icons/fa';
import { fetchKnowledgeBases } from '../api';

// Styled components for the knowledge selector
const KnowledgeContainer = styled.div`
  position: relative;
`;

const KnowledgeButton = styled.button`
  background: none;
  border: none;
  font-size: 16px;
  color: ${props => props.active ? '#4a6cf7' : '#666'};
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  padding: 0;
  transition: all 0.2s;
  
  &:hover {
    color: #4a6cf7;
    background-color: #efefef;
  }
`;

const BadgeCount = styled.span`
  background-color: #4a6cf7;
  color: white;
  border-radius: 50%;
  min-width: 14px;
  height: 14px;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: absolute;
  top: -2px;
  right: -2px;
  padding: 0 2px;
`;

const Dropdown = styled.div`
  position: absolute;
  bottom: calc(100% + 5px);
  left: 0;
  width: 280px;
  max-height: 350px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
`;

const DropdownHeader = styled.div`
  padding: 10px 12px;
  border-bottom: 1px solid #eee;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const SearchBox = styled.div`
  padding: 8px 12px;
  border-bottom: 1px solid #eee;
  position: relative;
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 8px 12px 8px 32px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  
  &:focus {
    border-color: #4a6cf7;
  }
`;

const SearchIcon = styled.div`
  position: absolute;
  left: 22px;
  top: 50%;
  transform: translateY(-50%);
  color: #888;
`;

const KnowledgeList = styled.div`
  overflow-y: auto;
  max-height: 250px;
  
  &::-webkit-scrollbar {
    width: 5px;
  }
  
  &::-webkit-scrollbar-thumb {
    background-color: #ddd;
    border-radius: 5px;
  }
`;

const KnowledgeItem = styled.div`
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #f5f5f5;
  
  &:hover {
    background-color: #f9f9f9;
  }
  
  .name {
    flex: 1;
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
  }
  
  .checkbox {
    width: 18px;
    height: 18px;
    border: 1.5px solid ${props => props.selected ? '#4a6cf7' : '#aaa'};
    border-radius: 4px;
    margin-right: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    background-color: ${props => props.selected ? '#4a6cf7' : 'white'};
    transition: all 0.2s;
  }
`;

const SelectAllItem = styled.div`
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #eee;
  background-color: #f5f5f5;
  font-weight: 500;
  
  &:hover {
    background-color: #f0f0f0;
  }
  
  .name {
    flex: 1;
  }
  
  .checkbox {
    width: 18px;
    height: 18px;
    border: 1.5px solid ${props => props.selected ? '#4a6cf7' : '#aaa'};
    border-radius: 4px;
    margin-right: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    background-color: ${props => props.selected ? '#4a6cf7' : 'white'};
    transition: all 0.2s;
  }
`;

const EmptyState = styled.div`
  padding: 20px;
  text-align: center;
  color: #888;
`;

const LoadingState = styled.div`
  padding: 20px;
  text-align: center;
  color: #888;
`;

const KnowledgeSelector = ({ selectedKbs = [], onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef(null);
  
  // Load knowledge bases
  useEffect(() => {
    const loadKnowledgeBases = async () => {
      setLoading(true);
      try {
        const data = await fetchKnowledgeBases();
        if (data?.code === 200 && Array.isArray(data.data)) {
          setKnowledgeBases(data.data);
        } else {
          console.error('Knowledge base data is not in expected format:', data);
          setKnowledgeBases([]);
        }
      } catch (error) {
        console.error('Failed to load knowledge bases:', error);
        setKnowledgeBases([]);
      } finally {
        setLoading(false);
      }
    };
    
    loadKnowledgeBases();
  }, []);
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);
  
  // Filter knowledge bases based on search query
  const filteredKnowledgeBases = Array.isArray(knowledgeBases) 
    ? knowledgeBases.filter(kb => kb.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : [];
  
  // Handle knowledge base selection
  const handleSelect = (kb) => {
    let newSelected;
    
    if (selectedKbs.includes(kb.id)) {
      newSelected = selectedKbs.filter(id => id !== kb.id);
    } else {
      newSelected = [...selectedKbs, kb.id];
    }
    
    onChange(newSelected);
  };
  
  // Handle select all
  const handleSelectAll = () => {
    if (selectedKbs.length === filteredKnowledgeBases.length) {
      onChange([]);
    } else {
      onChange(filteredKnowledgeBases.map(kb => kb.id));
    }
  };
  
  const isAllSelected = filteredKnowledgeBases.length > 0 && 
    selectedKbs.length === filteredKnowledgeBases.length;
  
  return (
    <KnowledgeContainer ref={dropdownRef}>
      <KnowledgeButton 
        onClick={() => setIsOpen(!isOpen)}
        active={isOpen || selectedKbs.length > 0}
        title="选择知识库"
      >
        <FaBook />
        {selectedKbs.length > 0 && <BadgeCount>{selectedKbs.length}</BadgeCount>}
      </KnowledgeButton>
      
      {isOpen && (
        <Dropdown>
          <DropdownHeader>
            知识库
          </DropdownHeader>
          
          <SearchBox>
            <SearchIcon>
              <FaSearch size={14} />
            </SearchIcon>
            <SearchInput
              placeholder="搜索知识库"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </SearchBox>
          
          {loading ? (
            <LoadingState>加载中...</LoadingState>
          ) : (
            <>
              {filteredKnowledgeBases.length > 0 ? (
                <KnowledgeList>
                  <SelectAllItem 
                    onClick={handleSelectAll}
                    selected={isAllSelected}
                  >
                    <div className="checkbox">
                      {isAllSelected && <FaCheck size={12} />}
                    </div>
                    <div className="name">全选</div>
                  </SelectAllItem>
                  
                  {filteredKnowledgeBases.map(kb => (
                    <KnowledgeItem 
                      key={kb.id}
                      onClick={() => handleSelect(kb)}
                      selected={selectedKbs.includes(kb.id)}
                    >
                      <div className="checkbox">
                        {selectedKbs.includes(kb.id) && <FaCheck size={12} />}
                      </div>
                      <div className="name">{kb.name}</div>
                    </KnowledgeItem>
                  ))}
                </KnowledgeList>
              ) : (
                <EmptyState>
                  {Array.isArray(knowledgeBases) && knowledgeBases.length === 0 
                    ? "没有可用的知识库" 
                    : "无搜索结果"}
                </EmptyState>
              )}
            </>
          )}
        </Dropdown>
      )}
    </KnowledgeContainer>
  );
};

export default KnowledgeSelector; 